from switch import find_bom_blob_url
import c1_main
import c2_main


def run_sheet_3_and_4():
    
    bom_url = find_bom_blob_url()
    
    if bom_url:
        c1_main.run_case1_pipeline()
    else:
        c2_main.run_case2_pipeline()
    
    
if __name__ == "__main__":
    run_sheet_3_and_4()