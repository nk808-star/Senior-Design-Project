import os
import requests
import pandas as pd

def download_nhanes_file(cycle, file_desc, category, download_dir="nhanes_data"):
    category = category.lower()
    
    # 1. Mapping cycle name to the CDC URL year component
    cycle_mapping = {
        "1999-2000": "1999", "2001-2002": "2001", "2003-2004": "2003",
        "2005-2006": "2005", "2007-2008": "2007", "2009-2010": "2009",
        "2011-2012": "2011-2012", "2013-2014": "2013", "2015-2016": "2015", 
        "2017-2018": "2017"
    }
    
    cycle_year = cycle_mapping.get(cycle)
    if not cycle_year:  
        print(f"ERROR: Unrecognized cycle: {cycle}")
        return None

    # 2. NHANES file code mappings (Simplified & Integrated)
    nhanes_file_mapping = {
        "demographics": {
            "Demographic Variables & Sample Weights": {
                "1999": "DEMO", "2001": "DEMO_B", "2003": "DEMO_C", "2005": "DEMO_D",
                "2007": "DEMO_E", "2009": "DEMO_F", "2011-2012": "DEMO_G", 
                "2013": "DEMO_H", "2015": "DEMO_I", "2017": "DEMO_J"  
            }
        },
        "questionnaire": {
            "Diabetes": {  
                "1999": "DIQ", "2001": "DIQ_B", "2003": "DIQ_C", "2005": "DIQ_D",
                "2007": "DIQ_E", "2009": "DIQ_F", "2011-2012": "DIQ_G", 
                "2013": "DIQ_H", "2015": "DIQ_I", "2017": "DIQ_J"
            }
        }
    }

    # 3. Get the specific file code (e.g., DEMO_G)
    file_code = nhanes_file_mapping.get(category, {}).get(file_desc, {}).get(cycle_year)
    if not file_code:
        print(f"ERROR: No mapping for {file_desc} in cycle {cycle}")
        return None
    
    # 4. URL construction & Directory setup
    url = f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/{cycle_year}/{file_code}.XPT"
    os.makedirs(download_dir, exist_ok=True)
    xpt_path = os.path.join(download_dir, f"{file_code}.XPT")
          
    # 5. Download logic
    if not os.path.exists(xpt_path):
        print(f"Downloading {file_code} from {url}...")
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                with open(xpt_path, "wb") as f:
                    f.write(response.content)
            else:
                print(f"ERROR: Status {response.status_code} for URL: {url}")
                return None
        except Exception as e:
            print(f"Download failed: {e}")
            return None
         
    # 6. Reading and Processing
    try:
        df = pd.read_sas(xpt_path, format='xport')
        
        # Ensure SEQN is always present for merging later
        if "SEQN" not in df.columns:
             # In some XPT files, SEQN might be read as a float; we usually want it as int
             print(f"Warning: SEQN not found in {file_code}")

        # Column filtering based on category
        if category == "demographics":
            cols = ["SEQN", "RIDAGEYR", "RIAGENDR", "RIDRETH1"]
            # Check if columns exist before filtering to avoid KeyErrors
            df = df[[c for c in cols if c in df.columns]]
            
        elif category == "questionnaire" and "Diabetes" in file_desc:
            if "DIQ010" in df.columns:
                df = df[["SEQN", "DIQ010"]]
                df.rename(columns={"DIQ010": f"DIQ010_{cycle.replace('-', '_')}"}, inplace=True)
            else:
                print(f"WARNING: DIQ010 not found in {file_code}")

        # Cleanup: Remove the file after loading into memory if desired
        # os.remove(xpt_path) 
        return df
            
    except Exception as e:
        print(f"ERROR reading {file_code}.XPT: {e}")
        return None