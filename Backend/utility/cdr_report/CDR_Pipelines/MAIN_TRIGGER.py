from utility.cdr_report.CDR_Pipelines.switch import find_bom_blob_url
import utility.cdr_report.CDR_Pipelines.c1_main as c1_main
import utility.cdr_report.CDR_Pipelines.c2_main as c2_main


def run_sheet_3_and_4():
    
    bom_url = find_bom_blob_url()
    
    if bom_url:
        c1_main.run_case1_pipeline()
    else:
        c2_main.run_case2_pipeline()
    
    
if __name__ == "__main__":
    run_sheet_3_and_4()