# case1.py
import utility.cdr_report.CDR_Pipelines.c1_extractor as c1_extractor
import utility.cdr_report.CDR_Pipelines.c1_tagger as c1_tagger
import utility.cdr_report.CDR_Pipelines.c1_formatter as c1_formatter
import utility.cdr_report.CDR_Pipelines.c1_master_bom as c1_master_bom
import utility.cdr_report.CDR_Pipelines.configs as configs

def run_case1_pipeline(*, vs):
    configs.require_runtime()


    print("Step 1 : Creating Master BOM . . .")
    c1_master_bom.run_master_bom(vs=vs)
    
    print("Step 2 : Extracting . . .")
    c1_extractor.run_extraction()
    
    print("Step 3 : Tagging Photos . . .")
    c1_tagger.run_phototagging()
    
    print("Step 4 : Formatting JSON . . .")
    c1_formatter.run_formatter()

