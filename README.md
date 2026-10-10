# MO-IT150 SPI Data Analytics Job Posting Analysis

This repository supports the **MO-IT150 Social and Professional Issues** Professional Issue Analysis:

> **Alignment Between Entry-Level Data Analyst Job Requirements and Fresh Graduate Qualifications Across Online Job Platforms and Local Employers in the Philippines**

The repository preserves the job-posting dataset, cleaning and normalization workflow, analysis notebooks, and visualizations used to examine employer requirements for entry-level Data Analytics-related roles.

## Research purpose

The analysis asks:

> What qualifications, skills, tools, education, and experience are being requested in Philippine entry-level Data Analytics-related job postings, and how do those requirements compare with documented graduate competencies and curricula?

The dataset is **not** used to assume that a nationwide skills mismatch exists. Findings are limited to the collected postings and the documented curriculum sources used in the study.

## Source and collection boundary

The initial candidate pool came from the following filtered SimplifyTrabaho page:

<https://simplifytrabaho.ycells.com/?level=internship%2Centry&nolevel=1&fn=data>

As observed on **October 9, 2026**:

- **364 roles**
- **93 companies**
- **276 saved HTML job pages** available for detailed processing
- **276 HTML pages successfully parsed**
- **0 parsing failures**
- **91 companies** represented in the parsed HTML subset
- **276 unique original source URLs**

The 276 downloaded pages are a subset of the 364-role live candidate pool. They should not be treated as the complete population of postings shown by the live page.

The SimplifyTrabaho `Data & AI` filter is broader than the study's target population. It contains Data Analytics roles as well as Data Engineering, Data Science, AI, data operations, annotation, architecture, data entry, and other adjacent roles. A second-stage scope screen was therefore applied.

## Data preparation workflow

```text
364 live candidate roles
        |
        v
276 saved HTML pages
        |
        v
HTML parsing and structured extraction
        |
        v
276-record screening audit
        |
        +--> Exclude non-analytics and adjacent roles
        |
        +--> Retain direct Data Analytics-related roles
        |
        v
74 direct Data Analytics-related postings
        |
        +--> 66 unique requirement profiles
        |
        +--> 26 confirmed entry-level postings
        |
        +--> remaining seniority cases retained for review/exclusion
        |
        v
Normalized skills and competency datasets
        |
        v
Google Colab analysis and visualization
```

## Current normalized dataset

### Role-scope screening

After conservative normalization:

| Dataset | Records | Purpose |
|---|---:|---|
| Raw parsed postings | 276 | Complete parsed evidence pool |
| Direct Data Analytics-related postings | 74 | Cleaned analytics-role dataset |
| Unique requirement profiles | 66 | Deduplicated analytical dataset |
| Confirmed entry-level Data Analytics postings | 26 | Strict entry-level subset |
| Scope-review queue | 4 | Roles requiring final manual scope decision |
| Normalized skill observations | 377 | Skill/tool and competency analysis |
| Entry-level skill observations | 104 | Skill/tool analysis for the strict entry-level subset |

The **66 unique requirement profiles** are recommended for general employer-requirement charts because identical employer/title/qualification templates can otherwise overweight repeated or multi-location postings.

The **26 confirmed entry-level postings** are recommended for the strict comparison with the graduate curriculum baseline.

### Included role families

| Role family | Count |
|---|---:|
| Data Analyst | 29 |
| Analytics Specialist | 13 |
| Reporting Analytics | 11 |
| Business Intelligence | 11 |
| Risk Analytics | 2 |
| Statistical Analytics | 2 |
| Visualization Analytics | 2 |
| Analytics Analyst | 2 |
| Marketing Analytics | 1 |
| Business Analytics | 1 |

### Entry-level normalization

Among the 74 direct Data Analytics-related postings:

| Entry-level classification | Count |
|---|---:|
| Confirmed entry-level | 26 |
| Entry-level unclear | 31 |
| Experience requirement of 3+ years | 8 |
| Explicitly not entry-level | 5 |
| Experience range extends above 2 years | 4 |

The strict entry-level subset uses explicit fresh-graduate, junior, or entry-level evidence and experience requirements that can reasonably be interpreted as entry-level. Ambiguous cases are not automatically forced into the subset.

## Scope rules

The main analytical dataset keeps roles whose primary function is directly connected to:

- data analysis
- analytical reporting
- business intelligence
- data visualization and dashboards
- statistical analytics
- domain-specific analytics
- closely related decision-support analytics

The main dataset excludes roles whose primary function is instead:

- Data Engineering
- Data Architecture
- Data Science when the role is not an analyst role
- AI or Machine Learning engineering
- data annotation or AI training
- data entry or encoding
- master/reference data administration
- data governance-only work
- data operations
- systems or application support
- database administration
- internships
- other roles where data is incidental rather than the main analytical function

All inclusion and exclusion decisions are retained in the screening audit rather than deleted.

## Skills and competency normalization

The original skills dataset was normalized so that specific tools can be distinguished from broader competencies.

| Extracted item | Item type | Normalized competency group |
|---|---|---|
| SQL | Tool | Database & querying |
| Power BI | Tool | Visualization & dashboards |
| Tableau | Tool | Visualization & dashboards |
| Excel | Tool | Spreadsheet analysis |
| Python | Tool | Programming for analytics |
| Data visualization | Competency | Visualization & dashboards |
| Statistical analysis | Competency | Statistics & quantitative analysis |
| Data quality | Competency | Data preparation & quality |
| Reporting | Competency | Reporting & communication |
| Machine learning | Competency | Machine learning & predictive analytics |

Skill evidence is also separated into:

- **Explicit required**
- **Explicit preferred**
- **Role responsibility / use**
- **Mention / unclear**
- **Required - wording needs review**
- **Preferred - wording needs review**

This avoids treating every skill mentioned anywhere in a posting as a mandatory requirement.

## Files

Recommended repository structure:

```text
MO-IT150_SPI_DataAnalytics_JobPostingAnalysis/
|
|-- notebooks/
|   `-- job_posting_analysis.ipynb
|
|-- data/
|   `-- processed/
|       |-- job_postings_direct_analytics_clean.csv
|       |-- job_profiles_direct_analytics_dedup.csv
|       |-- job_postings_entry_level_confirmed.csv
|       |-- skills_direct_analytics_clean.csv
|       |-- skills_entry_level_confirmed.csv
|       |-- role_screening_audit.csv
|       |-- role_scope_review_queue.csv
|       `-- normalization_summary.csv
|
`-- README.md
```

### Dataset descriptions

- `job_postings_direct_analytics_clean.csv`  
  All postings retained after the direct Data Analytics scope screen.

- `job_profiles_direct_analytics_dedup.csv`  
  Deduplicated requirement profiles for aggregate employer-demand analysis.

- `job_postings_entry_level_confirmed.csv`  
  Strict subset used for entry-level analysis.

- `skills_direct_analytics_clean.csv`  
  Long-format normalized skill/tool observations for all retained direct analytics roles.

- `skills_entry_level_confirmed.csv`  
  Long-format normalized skill/tool observations for the confirmed entry-level subset.

- `role_screening_audit.csv`  
  Complete 276-record audit trail showing inclusion, exclusion, and normalization decisions.

- `role_scope_review_queue.csv`  
  Small set of roles requiring manual scope confirmation.

- `normalization_summary.csv`  
  High-level counts for quality assurance and reproducibility.

## Curriculum data files

```text
HEI/
|-- hei_source_inventory.csv
|-- hei_curriculum_evidence_long.csv
|-- hei_core_competency_matrix.csv
`-- ched_reference_competencies.csv
```

These files are notebook-ready and are intended to support curriculum coverage charts and the employer-requirement versus curriculum comparison.

## Research boundaries and limitations

1. The initial live page contained 364 roles, but detailed analysis is limited to the 276 saved HTML pages available for processing.
2. The source filter covered the broader `Data & AI` category, so study-specific screening was necessary.
3. Classification is based on content preserved in the saved HTML files. Some dynamically loaded content may not have been captured.
4. A posting is not considered entry-level solely because SimplifyTrabaho categorized it as entry-level.
5. Required and preferred qualifications are separated where wording supports that distinction. Ambiguous statements remain marked for review.
6. Specific software tools are distinguished from broader Data Analytics competencies.
7. Repeated job templates can inflate frequency counts, so deduplicated requirement profiles are available for aggregate analysis.
8. The dataset describes the collected job-posting sample and does not establish nationwide employer behavior by itself.
9. The job-posting evidence does not, by itself, establish a mismatch between graduate preparation and employer expectations.
10. Curriculum comparison will use documented competencies rather than assuming that every graduate has mastered every competency taught in a program.


## Higher-education curriculum baseline

The curriculum side of the analysis uses a selected set of Philippine higher-education programs with Data Analytics, Data Science, Business Analytics, or closely related computing-analytics offerings. The purpose is to establish a **documented curriculum and graduate-competency baseline**, not to rank institutions or claim that the selected programs represent every Philippine graduate.

The source inventory currently contains **10 HEIs**, of which **8 provide enough public course or competency detail for direct coding**. The University of the Cordilleras and University of San Carlos are retained in the source inventory because they offer relevant programs, but they are excluded from competency counts until more detailed official curriculum evidence is available. CHED CMO No. 25, s. 2015 is treated separately as a national computing-program reference framework rather than as an HEI.

### HEI source inventory

| Institution | Program | Evidence available | Analytical use |
|---|---|---|---|
| Mapúa Malayan Digital College | BSIT, Data Analytics | Strong course and competency detail | Included |
| University of Santo Tomas | BS Data Science and Analytics | Full curriculum | Included |
| De La Salle University | BS Data Science | Strong program-outcome and tool evidence | Included |
| Mapúa University | BS Data Science | Explicit competency evidence; no full curriculum in captured source | Included with limitation |
| FEU Institute of Technology | BSIT, Business Analytics | Explicit specialization competencies | Included |
| Nueva Vizcaya State University | BSIS, Business Analytics | Program and specialization competency evidence | Included with limitation |
| University of Science and Technology of Southern Philippines | BS Data Science | Full curriculum | Included |
| University of the Immaculate Conception | BSIT, Analytics and Machine Intelligence | Full BSIT prospectus with analytics courses/concentration | Included |
| University of the Cordilleras | BS Data Analytics | Program offering confirmed; insufficient detailed curriculum | Source inventory only |
| University of San Carlos | BS Data Science | Program offering confirmed; insufficient detailed curriculum | Source inventory only |
| CHED CMO No. 25, s. 2015 | National BSCS/BSIS/BSIT framework | National outcomes and minimum/common computing curriculum | Reference framework only |

Official source URLs and detailed evidence are stored in:

- `HEI/hei_source_inventory.csv`
- `HEI/hei_curriculum_evidence_long.csv`
- `HEI/hei_core_competency_matrix.csv`
- `HEI/ched_reference_competencies.csv`

### Core curriculum competency matrix

Codes:

- **D** = explicitly documented in the reviewed official source
- **ND** = not documented in the reviewed source
- **IE** = available public evidence is insufficient for equivalent comparison

`ND` means only that the competency was not documented in the material reviewed. It must **not** be interpreted as proof that the institution does not teach the competency.

| Institution | Data prep | Analysis | Statistics | Database | Visualization | Reporting | Programming | ML / Predictive | BI / Decision support |
|---|---|---|---|---|---|---|---|---|---|
| Mapúa Malayan Digital College | D | D | ND | D | D | D | D | D | D |
| University of Santo Tomas | ND | D | D | D | D | D | D | D | D |
| De La Salle University | D | D | D | D | D | D | D | ND | ND |
| Mapúa University | ND | D | D | ND | ND | ND | D | D | D |
| FEU Institute of Technology | D | D | D | D | ND | D | D | ND | D |
| Nueva Vizcaya State University | ND | D | ND | D | ND | D | ND | ND | D |
| University of Science and Technology of Southern Philippines | ND | D | D | D | D | D | D | D | ND |
| University of the Immaculate Conception | ND | D | D | D | ND | ND | D | D | D |
| University of the Cordilleras | IE | IE | IE | IE | IE | IE | IE | IE | IE |
| University of San Carlos | IE | IE | IE | IE | IE | IE | IE | IE | IE |

### Curriculum comparison boundary

The curriculum comparison evaluates **documented curriculum coverage**, not actual student mastery. Course titles and program outcomes are coded only when they provide a reasonable basis for the competency category. Specific software proficiency is not inferred from a general course title. For example, a Data Visualization course establishes documented visualization coverage, but it does not establish Power BI or Tableau proficiency unless the official source names that tool.

Because public curriculum detail differs substantially among institutions, the final charts should primarily report the **number of institutions with explicit documented competency evidence** rather than rank schools or assign an overall alignment score.

The employer-side and curriculum-side datasets will be joined at the normalized competency level, such as data analysis, statistics, database/data management, visualization, reporting, programming, machine learning/predictive analytics, and business intelligence/decision support.


## Planned analysis in Google Colab

The Colab notebook will use the normalized datasets to generate:

- distribution of retained Data Analytics role families
- confirmed entry-level versus non-entry-level/unclear classifications
- most frequently requested Data Analytics competencies
- most frequently mentioned tools
- explicitly required versus explicitly preferred skills
- experience-requirement distribution
- education-requirement distribution
- direct employer versus recruitment-agency representation
- curriculum competency coverage
- employer demand versus documented curriculum coverage

Detailed source tables and audit records can be retained in the appendices, while the main paper can use summary tables and charts for interpretation.

## Reproducibility

The raw HTML archive is intentionally kept outside the public repository. The repository should preserve the cleaned datasets, analysis notebook, methodology, and source URLs needed to trace the analytical results without republishing full employer job-description pages.

All automated classifications remain subject to human review before they are treated as final evidence in the MO-IT150 paper.
