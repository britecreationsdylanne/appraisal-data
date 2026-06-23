-- =============================================================================
-- DRAFT read-only flattening views for the real (normalized) appraisal schema.
--
-- Purpose: collapse appraisals -> jewelry_pieces -> stone tables (and watches)
-- into ONE ROW PER APPRAISED PIECE, with enum integers translated to labels and
-- cents converted to USD — matching the column names the semantic layer expects
-- (dimensions.yaml / metrics.yaml). The app then points `appraisals` -> appraisal_flat
-- and `watches` -> watch_flat (both VIEWS), changing nothing else.
--
-- STATUS: DRAFT — written from _private/appraisal-mcp-docs, NOT yet run against the
-- real DB. Verify column names/enum values on first connect. Read-only (CREATE VIEW).
--
-- Known gaps to confirm on connect:
--   * generation: no birthdate in `customers` -> not available (semantic drops it).
--   * customer_state: a customer may have multiple addresses; we take one.
--   * brand_name: only the brands the semantic layer filters on are mapped; others
--     collapse to 'other_brand' (expand as needed).
-- =============================================================================

CREATE OR REPLACE VIEW appraisal_flat AS
WITH largest_diamond AS (
    SELECT DISTINCT ON (jewelry_piece_id)
        jewelry_piece_id, source, shape, color_from, clarity_from, carats, setting
    FROM diamonds
    ORDER BY jewelry_piece_id, carats DESC NULLS LAST
),
largest_fancy AS (
    SELECT DISTINCT ON (jewelry_piece_id)
        jewelry_piece_id, color, intensity, carats
    FROM fancy_diamonds
    ORDER BY jewelry_piece_id, carats DESC NULLS LAST
),
largest_gem AS (
    SELECT DISTINCT ON (jewelry_piece_id)
        jewelry_piece_id, gemstone_type, grade, carats
    FROM gemstones
    ORDER BY jewelry_piece_id, carats DESC NULLS LAST
),
melee AS (
    SELECT jewelry_piece_id, SUM(total_carats) AS melee_total
    FROM diamond_melees GROUP BY jewelry_piece_id
),
mount AS (
    SELECT DISTINCT ON (jewelry_piece_id) jewelry_piece_id, metal, metal_grade
    FROM mountings ORDER BY jewelry_piece_id, id
),
cust_state AS (
    SELECT DISTINCT ON (addressable_id) addressable_id AS customer_id, state
    FROM addresses WHERE addressable_type = 'Customer' AND country = 'US'
    ORDER BY addressable_id, id
)
SELECT
    a.id AS appraisal_id,
    a.appraised_at::date AS appraisal_date,
    EXTRACT(YEAR FROM a.appraised_at)::int AS appraisal_year,
    (EXTRACT(YEAR FROM a.appraised_at)::int || ' Q' || EXTRACT(QUARTER FROM a.appraised_at)::int) AS year_quarter,

    -- briteco_category: category (+ piece_type for rings) -> the labels the tool uses
    CASE jp.category
        WHEN 1 THEN CASE jp.piece_type WHEN 1 THEN 'Engagement Ring'
                                       WHEN 2 THEN 'Wedding Band'
                                       ELSE 'Other Ring' END
        WHEN 2 THEN 'Bracelet'
        WHEN 3 THEN 'Earrings'
        WHEN 4 THEN 'Pendant'
        WHEN 5 THEN 'Necklace'
        ELSE 'Other'
    END AS briteco_category,
    jp.piece_type::text AS jewelry_type,        -- TODO: map piece_type enum -> label
    jp.style::text       AS piece_style,         -- TODO: map style enum -> label
    NULL::text           AS type_and_style,      -- TODO: compose category + style label

    -- Largest diamond
    CASE ld.source WHEN 0 THEN 'natural' WHEN 1 THEN 'lab' END AS largest_diamond_source,
    CASE ld.shape
        WHEN 1 THEN 'Round' WHEN 8 THEN 'Oval' WHEN 3 THEN 'Princess'
        WHEN 5 THEN 'Emerald' WHEN 6 THEN 'Emerald'
        WHEN 11 THEN 'Cushion' WHEN 12 THEN 'Cushion'
        WHEN 4 THEN 'Marquise' WHEN 2 THEN 'Pear'
        WHEN 9 THEN 'Radiant' WHEN 10 THEN 'Radiant'
        WHEN 7 THEN 'Asscher' WHEN 13 THEN 'Heart'
        ELSE 'Other'
    END AS shape,
    CASE
        WHEN ld.color_from BETWEEN 1 AND 3  THEN 'D-F'
        WHEN ld.color_from BETWEEN 4 AND 5  THEN 'G-H'
        WHEN ld.color_from BETWEEN 6 AND 7  THEN 'I-J'
        WHEN ld.color_from BETWEEN 8 AND 10 THEN 'K-M'
        WHEN ld.color_from BETWEEN 11 AND 23 THEN 'N-Z'
    END AS color_band,
    CASE
        WHEN ld.clarity_from IN (11, 2)     THEN 'IF/FL'
        WHEN ld.clarity_from IN (3, 4)      THEN 'VVS'
        WHEN ld.clarity_from IN (5, 6)      THEN 'VS'
        WHEN ld.clarity_from IN (7, 8, 12)  THEN 'SI'
        WHEN ld.clarity_from IN (9, 10, 13) THEN 'I'
    END AS clarity_band,
    ld.carats AS largest_diamond_weight,
    CASE
        WHEN ld.carats < 0.5 THEN '0.00-0.50' WHEN ld.carats < 1 THEN '0.50-1.00'
        WHEN ld.carats < 1.5 THEN '1.00-1.50' WHEN ld.carats < 2 THEN '1.50-2.00'
        WHEN ld.carats < 2.5 THEN '2.00-2.50' WHEN ld.carats < 3 THEN '2.50-3.00'
        WHEN ld.carats < 4 THEN '3.00-4.00' ELSE '>4.00'
    END AS carat_band,
    COALESCE(m.melee_total, 0) AS melee_diamond_total_weight,
    CASE ld.setting
        WHEN 1 THEN 'prong' WHEN 2 THEN 'bezel' WHEN 4 THEN 'channel'
        WHEN 5 THEN 'pave' WHEN 11 THEN 'scallop' ELSE 'other_setting'
    END AS setting,

    -- Fancy diamond
    (lf.jewelry_piece_id IS NOT NULL) AS is_fancy,
    lf.color AS fancy_color,            -- already Title Case string in source
    CASE lf.intensity
        WHEN 0 THEN 'Light' WHEN 1 THEN 'Fancy Light' WHEN 2 THEN 'Fancy'
        WHEN 3 THEN 'Fancy Intense' WHEN 4 THEN 'Fancy Vivid' WHEN 5 THEN 'Fancy Deep'
        WHEN 6 THEN 'Fancy Dark' WHEN 7 THEN 'Faint' WHEN 8 THEN 'Very Light'
    END AS fancy_intensity,

    -- Gemstone
    lg.gemstone_type AS largest_gemstone_type,
    CASE lg.grade WHEN 1 THEN 'AAA' WHEN 2 THEN 'AA' WHEN 3 THEN 'A' WHEN 4 THEN 'B' END AS gemstone_quality,

    -- Mounting
    CASE mo.metal
        WHEN 2 THEN 'white_gold' WHEN 3 THEN 'yellow_gold' WHEN 4 THEN 'rose_gold'
        WHEN 6 THEN 'platinum' WHEN 1 THEN 'no_metal' ELSE 'other'
    END AS metal,
    CASE mo.metal_grade
        WHEN 3 THEN 'fourteen_k' WHEN 4 THEN 'eighteen_k' WHEN 2 THEN 'ten_k'
        WHEN 7 THEN '950' WHEN 5 THEN '22k' WHEN 6 THEN '24k' ELSE 'no_grade'
    END AS metal_grade,

    -- Brand (only the ones the tool filters on; expand as needed)
    CASE jp.brand_name
        WHEN 1 THEN 'no_brand' WHEN 2 THEN 'cartier' WHEN 4 THEN 'tiffany'
        WHEN 6 THEN 'van_cleef_arpels' WHEN 12 THEN 'david_yurman' WHEN 17 THEN 'tacori'
        WHEN 30 THEN 'hearts_on_fire' WHEN 49 THEN 'verragio'
        ELSE 'other_brand'
    END AS brand_name,

    -- Value (cents -> USD)
    jp.sales_price_cents / 100.0 AS sales_price,
    a.selected_value_cents / 100.0 AS replacement_value,

    cs.state AS customer_state
FROM appraisals a
JOIN jewelry_pieces jp ON a.appraisable_type = 'JewelryPiece' AND a.appraisable_id = jp.id
LEFT JOIN largest_diamond ld ON ld.jewelry_piece_id = jp.id
LEFT JOIN largest_fancy   lf ON lf.jewelry_piece_id = jp.id
LEFT JOIN largest_gem     lg ON lg.jewelry_piece_id = jp.id
LEFT JOIN melee           m  ON m.jewelry_piece_id  = jp.id
LEFT JOIN mount           mo ON mo.jewelry_piece_id = jp.id
LEFT JOIN cust_state      cs ON cs.customer_id      = a.customer_id
WHERE a.appraised_at IS NOT NULL   -- finalized only
  AND a.status = 0;                -- active (not voided)


-- =============================================================================
-- watch_flat: one row per watch appraisal. The tool's Watch Report uses
-- brand / movement / case_material / complication (+ value). condition and
-- generation are NOT in the real watch schema — confirm/adjust on connect.
-- =============================================================================
CREATE OR REPLACE VIEW watch_flat AS
SELECT
    a.id AS appraisal_id,
    a.appraised_at::date AS appraisal_date,
    EXTRACT(YEAR FROM a.appraised_at)::int AS appraisal_year,
    (EXTRACT(YEAR FROM a.appraised_at)::int || ' Q' || EXTRACT(QUARTER FROM a.appraised_at)::int) AS year_quarter,
    w.brand_name      AS brand,
    w.movement        AS movement,
    w.case_material   AS case_material,
    w.functions       AS complication,     -- free text; may need normalizing
    w.sales_price_cents  / 100.0 AS sales_price,
    a.selected_value_cents / 100.0 AS replacement_value,
    cs.state AS customer_state
FROM appraisals a
JOIN watches w ON a.appraisable_type = 'Watch' AND a.appraisable_id = w.id
LEFT JOIN (
    SELECT DISTINCT ON (addressable_id) addressable_id AS customer_id, state
    FROM addresses WHERE addressable_type = 'Customer' AND country = 'US'
    ORDER BY addressable_id, id
) cs ON cs.customer_id = a.customer_id
WHERE a.appraised_at IS NOT NULL
  AND a.status = 0;
