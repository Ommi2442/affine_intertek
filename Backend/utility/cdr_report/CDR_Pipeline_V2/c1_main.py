# case1.py
import c1_extractor
import c1_tagger
import c1_formatter
import c1_master_bom

def run_case1_pipeline():
    
    print("Step 1 : Creating Master BOM . . .")
    c1_master_bom.run_master_bom()
    
    print("Step 2 : Extracting . . .")
    c1_extractor.run_extraction()
    
    print("Step 3 : Tagging Photos . . .")
    c1_tagger.run_phototagging()
    
    print("Step 4 : Formatting JSON . . .")
    c1_formatter.run_formatter()

