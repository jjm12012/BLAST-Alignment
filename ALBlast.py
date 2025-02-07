import os
import pandas as pd
import requests
import streamlit as st
import time
import zipfile
from Bio import SeqIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill

# Streamlit UI
st.title("🔬 BLAST Analysis Tool")
st.write("Upload your .ab1 files, and the script will process them, run alignments, and generate an Excel summary.")

# Step 1: File Upload
uploaded_files = st.file_uploader("Upload .ab1 Files", type=["ab1"], accept_multiple_files=True)
reference_file = st.file_uploader("Upload Reference Sequence (.txt)", type=["txt"])

def run_ncbi_blast(query_fasta, output_file):
    url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
    
    with open(query_fasta, "r") as f:
        query_seq = f.read()
    
    params = {
        "CMD": "Put",
        "PROGRAM": "blastn",
        "DATABASE": "nt",
        "QUERY": query_seq,
        "FORMAT_TYPE": "Text"
    }
    headers = {'User-Agent': 'Mozilla/5.0'}  # Helps avoid request blocking
    response = requests.post(url, data=params, headers=headers)
    
    if "RID" not in response.text:
        raise ValueError("BLAST job submission failed.")
    
    rid = response.text.split("RID = ")[1].split("\n")[0].strip()
    print(f"BLAST job submitted. Request ID: {rid}")
    
    time.sleep(30)
    
    params_check = {
        "CMD": "Get",
        "RID": rid,
        "FORMAT_TYPE": "Text"
    }
    
    while True:
        result = requests.get(url, params=params_check)
        if "Status=READY" in result.text:
            break
        time.sleep(10)
    
    with open(output_file, "w") as f:
        f.write(result.text)
    print("BLAST results saved.")

if uploaded_files and reference_file:
    with st.spinner("Processing files..."):
        base_dir = "blast_workspace"
        fasta_dir = os.path.join(base_dir, "FASTA_Files")
        blast_output_dir = os.path.join(base_dir, "BLAST_Results")
        os.makedirs(fasta_dir, exist_ok=True)
        os.makedirs(blast_output_dir, exist_ok=True)
        
        reference_fasta = os.path.join(base_dir, "reference.fasta")
        with open(reference_fasta, "w") as ref_fasta:
            ref_fasta.write(">Reference_Sequence\n")
            ref_fasta.write(reference_file.getvalue().decode("utf-8"))
        
        for uploaded_file in uploaded_files:
            fasta_filename = uploaded_file.name if hasattr(uploaded_file, 'name') else str(uploaded_file)
            file_path = os.path.join(fasta_dir, fasta_filename.replace(".ab1", ".fasta"))
            
            with open(file_path, "w") as fasta_file:
                record = SeqIO.read(uploaded_file, "abi")
                trimmed_seq = record.seq[20:]
                record.letter_annotations = {}
                record.seq = trimmed_seq
                SeqIO.write(record, fasta_file, "fasta")
        
        st.success("✅ Files converted to FASTA successfully!")
        
        summary_data = []
        for fasta_file in os.listdir(fasta_dir):
            if not fasta_file.endswith(".fasta"):
                continue
            query_fasta = os.path.join(fasta_dir, fasta_file)
            output_file = os.path.join(blast_output_dir, fasta_file.replace(".fasta", "_blast_results.txt"))
            run_ncbi_blast(query_fasta, output_file)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                score, expect, identities, gaps, strand = "", "", "", "", ""
                with open(output_file, "r") as file:
                    for line in file:
                        if "Score =" in line:
                            score = line.split("=")[1].strip().split()[0]
                        elif "Expect =" in line:
                            expect = line.split("=")[1].strip().split()[0] if "=" in line else "N/A"
                        elif "Identities =" in line:
                            identities = line.split("=")[1].strip().split(",")[0]
                        elif "Gaps =" in line:
                            gaps = line.split("=")[1].strip().split(",")[0] if "=" in line else "N/A"
                        elif "Strand =" in line:
                            strand = line.split("=")[1].strip()
                summary_data.append([fasta_file, score, expect, identities, gaps, strand])
            else:
                st.error(f"❌ No BLAST output found for {fasta_file}. Check your input sequences!")
        
        st.success("✅ BLAST alignment completed!")
        
        excel_summary_file = os.path.join(blast_output_dir, "BLAST_Summary.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.title = "BLAST Results"
        headers = ["Query File", "Score", "Expect", "Identities", "Gaps", "Strand"]
        ws.append(headers)
        for row in summary_data:
            ws.append(row)
        wb.save(excel_summary_file)
        st.success("✅ BLAST summary saved!")
        
        with open(excel_summary_file, "rb") as f:
            st.download_button(
                label="📥 Download BLAST Summary",
                data=f,
                file_name="BLAST_Summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
