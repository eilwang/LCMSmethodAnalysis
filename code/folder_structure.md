```text

BPS2026
└─ artifact-export.zip
    └── processing-runs
│       ├── <sample+search_specific UUID>
        ├── <sample+search_specific UUID>
        └── <sample+search_specific UUID>
            └── p8s
                ├── tims-diann.peptide.parquet
                ├── tims-diann.protein.parquet
                └── tims-diann.result.zip
                    ├── results.tsv
                    ├── results.genes.tsv
                    ├── results.gg_matrix.tsv
                    ├── results.gg_max_lfq_matrix.tsv
                    ├── results.pg_matrix.tsv
                    ├── results.pg_max_lfq_matrix.tsv
                    ├── results.pr_matrix.tsv
                    └── results.unique_genes_matrix.tsv

BPS2025

├── artifact-export.zip
│   └── processing-runs
│       ├── <sample+search_specific UUID>
│       ├── <sample+search_specific UUID>
│       └── <sample+search_specific UUID>
│           ├── tims-diann.peptide.parquet
│           ├── tims-diann.protein.parquet
│           └── tims-diann.result.zip
│               ├── results.tsv
│               ├── results.genes.tsv
│               ├── results.gg_matrix.tsv
│               ├── results.gg_max_lfq_matrix.tsv
│               ├── results.pg_matrix.tsv
│               ├── results.pg_max_lfq_matrix.tsv
│               ├── results.pr_matrix.tsv
│               └──  results.unique_genes_matrix.tsv


fragpipe_NF

folder
├── CZB-MAP
│   └── Nextflow
│       ├── reports
│       │   └── CZB-Map_proteomics_report.html
│       └── data_tables
│           ├── wide_format_data.csv
│           ├── msstats_statistics.csv
│           ├── imputed_statistics.csv
│           ├── imputed_wide_format_data.csv
│           ├── feature_data.csv
│           ├── metadata.csv
│           ├── MSstats_raw.csv
│           ├── enriched_data.csv
│           ├── enrichment_metadata.csv
│           ├── ensemble_enrichment_dataframe.csv
│           ├── GO_GSEA_enrichment.csv
│           ├── GO_GSEA_object.rds
│           ├── GO_GSEA_summary.csv
│           ├── kegg_module_dataframe.csv
│           ├── kegg_module_summary.csv
│           ├── kegg_pathways_dataframe.csv
│           ├── msstats_peptide_feature_fata.csv
│           ├── peptide_viz_data.RData
│           ├── reactome_enrichment_dataframe.csv
│           └── reactome_GPT_summary_dataframe.csv
├── <>.manifest
├── <>.workflow
└── workingDir
    ├── ion.tsv
    ├── peptide.tsv
    ├── protein.tsv
    ├── psm.tsv
    ├── library.tsv
    └── diann-output
            ├── report.tsv
            ├── msstats.tsv
            ├── msstats_ptm.tsv
            ├── report.pg_matrix.tsv
            ├── report.pr_matrix.tsv
            ├── report.gg_matrix.tsv
            ├── report.tsv
            ├── report.stats.tsv
            ├── report.unique_genes_matrix.tsv
            └── report.log.txt