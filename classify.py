from google import genai
from google.genai import types
import pandas as pd
import json
import time

# ---------------------------
# Settings
# ---------------------------
#API_KEY = "API Key"
INPUT_CSV = "file_profiles.csv"
OUTPUT_CSV = "classifications.csv"
BATCH_SIZE = 100
MODEL = "gemini-2.0-flash" 

SYSTEM_PROMPT = """
You are an information security analyst specializing in data classification 
according to BSI IT-Grundschutz. Your task is to assess the Schutzbedarf 
(protection needs) of files based on their access patterns and metadata.

For each file you receive, you must classify it across four Schutzziele:

1. Vertraulichkeit (Confidentiality)
* Preserving authorized restrictions on information access and disclosure, including means for protecting personal privacy and proprietary information.
   - Who accessed the file? Privileged roles (CEO, CFO, HR) signal higher sensitivity.
   - How many users and departments accessed it? Low access_ratio = likely confidential.
   - single_department_file = 1 means it stayed within one team = likely internal/confidential.
   - The file extension gives context (.doc, .pdf vs .zip, .exe).

2. Integrität (Integrity)
* Guarding against improper information modification or destruction, and includes ensuring information nonrepudiation and authenticity. 
   - Would unauthorized modification of this file cause harm?
   - Files accessed by few high-privilege roles and rarely modified suggest 
     high integrity requirements.
   - top_user_access_ratio close to 1.0 means one person dominates access = 
     potential single point of failure for integrity.

3. Verfügbarkeit (Availability)
* Ensuring timely and reliable access to and use of information. 
   - How business-critical is this file?
   - High access_frequency and many unique users = many people depend on it = 
     higher availability need.
   - Short access_span_days with low frequency = possibly one-time use = 
     lower availability need.


Classification scale (NIST FIPS 199):
Vertraulichkeit:
Low: The unauthorized disclosure of information could be expected to have a limited adverse effect on organizational operations, organizational assets, or individuals.
Moderate: The unauthorized disclosure of information could be expected to have a serious adverse effect on organizational operations, organizational assets, or individuals.
High: The unauthorized disclosure of information could be expected to have a severe or catastrophic adverse effect on organizational operations, organizational assets, or individuals. 

Integrity:
Low: The unauthorized modification or destruction of information could be expected to have a limited adverse effect on organizational operations, organizational assets, or individuals. 
Moderate: The unauthorized modification or destruction of information could be expected to have a serious adverse effect on organizational operations, organizational assets, or individuals.
High: The unauthorized modification or destruction of information could be expected to have a severe or catastrophic adverse effect on organizational operations, organizational assets, or individuals. 

Availibility:
Low: The disruption of access to or use of information or an information system could be expected to have a limited adverse effect on organizational operations, organizational assets, or individuals.
Moderate: The disruption of access to or use of information or an information system could be expected to have a serious adverse effect on organizational operations, organizational assets, or individuals. 
High: The disruption of access to or use of information or an information system could be expected to have a severe or catastrophic adverse effect on organizational operations, organizational assets, or individuals.

You will receive a batch of file profiles in CSV format. 
Respond ONLY with a valid JSON array. No explanation, no markdown, no preamble.
Each element must have exactly these keys:
filename, vertraulichkeit, vertraulichkeit reasoning, integritaet, integritaet reasoning, verfuegbarkeit, verfuegbarkeit reasoning

The reasoning field should be 2-3 sentences maximum.
"""

# ---------------------------
# Setup
# ---------------------------
#client = genai.Client(api_key=API_KEY)

# ---------------------------
# Load profiles
# ---------------------------
df = pd.read_csv(INPUT_CSV)
results = []

# ---------------------------
# Batch processing
# ---------------------------
def build_batch_prompt(batch_df):
    return "Classify the following file profiles:\n\n" + batch_df.to_csv(index=False)

def process_batch(batch_df):
    prompt = build_batch_prompt(batch_df)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,  # low = more consistent outputs
        )
    )
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

# ---------------------------
# Main loop
# ---------------------------
total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE

for i in range(5):  # test with 25 batches first
    batch = df.iloc[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
    print(f"Processing batch {i+1}/{total_batches}...")

    try:
        batch_results = process_batch(batch)
        results.extend(batch_results)
    except Exception as e:
        print(f"  Error on batch {i+1}: {e}")
        for _, row in batch.iterrows():
            results.append({
                "filename": row["filename"],
                "vertraulichkeit": None,
                "vertraulichkeit reasoning": f"ERROR: {str(e)}",
                "integritaet": None,
                "integritaet reasoning": f"ERROR: {str(e)}",
                "verfuegbarkeit": None,
                "verfuegbarkeit reasoning": f"ERROR: {str(e)}",
            })

    time.sleep(3)

# ---------------------------
# Save
# ---------------------------
out = pd.DataFrame(results)
out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
print(f"Done. {len(out)} classifications written to {OUTPUT_CSV}")

###########################################
#NOTE:
# Due to git policies API keys can not be neither commited nor uploaded, please remove "#" sign from lines 10 and 74 + make sure to paste the correct API key
###########################################
