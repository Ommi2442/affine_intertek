# main.py
import utility.cdr_report.CDR_Pipelines.c2_extractor as c2_extractor
import utility.cdr_report.CDR_Pipelines.c2_processor as c2_processor
import utility.cdr_report.CDR_Pipelines.c2_formatter as c2_formatter
import utility.cdr_report.CDR_Pipelines.configs as configs

def run_case2_pipeline():
    configs.require_runtime()
    
    print("Step 1 : Extracting . . .")
    c2_extractor.run_extractor()
    
    print("Step 2 : Processing . . .")
    c2_processor.run_processor()
    
    print("Step 3 : Formatting JSON . . .")
    c2_formatter.run_formatter()




#run_case2_pipeline()

    # 6. SUMMARY
    #print("\n===== TOKEN USAGE =====")
    #print("Prompt tokens     :", c2.utils.TOTAL_TOKENS["prompt"])
    #print("Completion tokens :", c2.utils.TOTAL_TOKENS["completion"])
    #print("Total tokens      :", c2.utils.TOTAL_TOKENS["total"])
    #print("=======================")

