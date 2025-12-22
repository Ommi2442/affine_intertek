# main.py
import c2_extractor
import c2_processor
import c2_formatter


def run_case2_pipeline():
     
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

