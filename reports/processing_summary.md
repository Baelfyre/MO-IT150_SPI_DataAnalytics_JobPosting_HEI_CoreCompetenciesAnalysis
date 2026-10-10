# Job-posting HTML processing summary

## Source and scope

- Initial live candidate pool: 364 roles across 93 companies on October 9, 2026 (user-provided context; not re-verified).
- Archive: `D:\AnalysisOutput\data\raw\JobPostingsHtmlFormat.zip`
- HTML files found in ZIP before processing: **276**.
- Successfully parsed: **276**.
- Failed to parse: **0**.
- Each saved HTML page is retained as one record; no records were merged or removed.

## Classification counts

- Data Analytics-related YES: **59**.
- Data Analytics-related NO: **10**.
- Data Analytics-related NEEDS_REVIEW: **207**.
- Entry-level status:
  - EXPLICIT_ENTRY_LEVEL: **36**.
  - ENTRY_LEVEL_WITH_EXPERIENCE: **18**.
  - POSSIBLE_ENTRY_LEVEL: **14**.
  - NOT_ENTRY_LEVEL: **42**.
  - UNCLEAR: **166**.
- Employer type:
  - Direct employer: **216**.
  - Recruitment agency: **39**.
  - Unclear: **21**.
- Unique companies represented (excluding unstated): **91**.
- Records with an HTTP/S original source URL captured in saved HTML: **276** (live reachability not checked).
- Skill rows: **907** across **211** postings.
- Records requiring review: **276**.

## Duplicate checks

- Duplicate original URL groups: **0**; records in those groups: **0**. Duplicate URLs are retained and flagged for review.
- Duplicate company and job-title groups: **2**; records in those groups: **11**. Similar postings are not merged automatically.

## Validation

- PASS: One dataset row exists for every HTML archive member.
- PASS: Posting IDs are unique and stable from source paths.
- PASS: Every processed row retains source_html_file.
- PASS: Data Analytics values use the allowed set.
- PASS: All NEEDS_REVIEW records appear in needs_review.csv.
- PASS: Every skills_long posting_id belongs to job_postings.csv.
- PASS: Experience wording is not emitted as a skill.
- PASS: Education credentials are not emitted as skills.
- PASS: Required skills and preferred qualifications are independently extracted.
- PASS: Each posting has at most one row per normalized skill.
- PASS: Parsed and failed counts reconcile to archive HTML count.
- PASS: Written job_postings.csv is readable and has the expected row count.
- PASS: Written skills_long.csv is readable and preserves all skill rows.
- PASS: Written needs_review.csv is readable and preserves all review rows.

## Review patterns and limitations

- Required versus preferred qualification wording needs review.: **242** record(s).
- Data Analytics relevance is ambiguous from the saved title and duties.: **207** record(s).
- Entry-level eligibility is not established decisively by the saved posting.: **180** record(s).
- Employer type cannot be determined from available page evidence.: **21** record(s).
- No recurring host-level company/title extraction gap affected two or more records.
- Saved HTML may omit content loaded dynamically after the page was saved; no live sites were revisited.
- Original source URL presence was checked from saved-page metadata only; live URL reachability was not checked.
- Descriptions in page metadata can be truncated or duplicate the visible page. Extraction uses JSON-LD, metadata, headings, labels, and visible text; missing evidence remains `Not stated` or is sent for review.
- Data Analytics and entry-level classifications are conservative rule-based screening labels, not final human coding. The SimplifyTrabaho filter was not used as proof of entry-level eligibility.
- Skills are limited to a transparent built-in list of common analytics tools and skills. Unrecognized terms are not guessed or normalized.
- BeautifulSoup 4 is the only non-standard Python dependency. The script makes no network requests and reads HTML directly from the ZIP without extracting or modifying it.

## Files created

- Script: `D:\AnalysisOutput\scripts\process_job_postings.py`
- Job postings: `D:\AnalysisOutput\data\processed\job_postings.csv`
- Long-format skills: `D:\AnalysisOutput\data\processed\skills_long.csv`
- Review queue: `D:\AnalysisOutput\data\processed\needs_review.csv`
- Summary: `D:\AnalysisOutput\reports\processing_summary.md`

## Safest next step for Google Colab

Copy the reviewed script and the unchanged ZIP into the Colab runtime (or a mounted Drive folder), then invoke the same script with explicit `--input`, `--output`, and `--reports` paths. Compare the ZIP HTML count and validation summary before using the CSVs in a notebook; keep analysis and curriculum comparison in a later, separately reviewed step.
