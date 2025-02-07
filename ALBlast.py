import os
import subprocess
import pandas as pd
import streamlit as st
import zipfile
from Bio import SeqIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill

# Streamlit UI
st.title("🔬 BLAST Analysis Tool")
st.write("Upload your .ab1 files, and the script will process them, create a BLAST database, run alignments, and generate an Excel summary.")

# Step 1: File Upload
uploaded_files = st.file_uploader("Upload .ab1 Files", type=["ab1"], accept_multiple_files=True)
reference_file = st.file_uploader("Upload Reference Sequence (.txt)", type=["txt"])

if uploaded_files and reference_file:
    with st.spinner("Processing files..."):
        base_dir = "blast_workspace"
        fasta_dir = os.path.join(base_dir, "FASTA_Files")
        blast_output_dir = os.path.join(base_dir, "BLAST_Results")
        blast_db_dir = os.path.join(base_dir, "BLAST_DB")

        os.makedirs(fasta_dir, exist_ok=True)
        os.makedirs(blast_output_dir, exist_ok=True)
        os.makedirs(blast_db_dir, exist_ok=True)

        reference_fasta = os.path.join(base_dir, "reference.fasta")
        with open(reference_fasta, "w") as ref_fasta:
            ref_fasta.write(">Reference_Sequence\n")
            ref_fasta.write(reference_file.getvalue().decode("utf-8"))

        for uploaded_file in uploaded_files:
            file_path = os.path.join(fasta_dir, uploaded_file.name.replace(".ab1", ".fasta"))
            with open(file_path, "w") as fasta_file:
                record = SeqIO.read(uploaded_file, "abi")
                trimmed_seq = record.seq[20:]
                record.letter_annotations = {}
                record.seq = trimmed_seq
                SeqIO.write(record, fasta_file, "fasta")

        st.success("✅ Files converted to FASTA successfully!")

        blast_db_path = os.path.join(blast_db_dir, "reference_db")
        makeblastdb_cmd = f'makeblastdb -in "{reference_fasta}" -dbtype nucl -out "{blast_db_path}"'
        subprocess.run(makeblastdb_cmd, shell=True, check=True)

        st.success("✅ BLAST database created successfully!")

        summary_data = []
        for fasta_file in os.listdir(fasta_dir):
            query_fasta = os.path.join(fasta_dir, fasta_file)
            output_file = os.path.join(blast_output_dir, fasta_file.replace(".fasta", "_blast_results.txt"))
            blastn_cmd = f'blastn -query "{query_fasta}" -db "{blast_db_path}" -out "{output_file}" -outfmt "0"'
            subprocess.run(blastn_cmd, shell=True, check=True)

            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                score, expect, identities, gaps, strand = "", "", "", "", ""
                with open(output_file, "r") as file:
                    for line in file:
                        if "Score =" in line:
                            score = line.split("=")[1].strip().split()[0]
                        elif "Expect =" in line:
                            expect = line.split('=')[1].strip().split()[0] if '=' in line and len(line.split('=')) > 1 else 'N/A' if "=" in line else "N/A"
                            expect = line.split("=")[-1].strip().split()[0] if "=" in line else "N/A"
                            expect = line.split("=")[1].strip().split()[0] if "=" in line and len(line.split("=")) > 1 else "N/A"
                            expect = line.split("=")[1].strip().split()[0] if "=" in line else ""
                            expect = line.split("=")[1].strip().split()[0]
                        elif "Identities =" in line:
                            identities = line.split("=")[1].strip().split(",")[0]
                        elif "Gaps =" in line:
                            gaps = line.split('=')[1].strip().split(',')[0] if '=' in line and len(line.split('=')) > 1 else 'N/A' if "=" in line else "N/A"
                            gaps = line.split("=")[-1].strip().split(",")[0] if "=" in line else "N/A"
                            gaps = line.split("=")[1].strip().split(",")[0] if "=" in line and len(line.split("=")) > 1 else "N/A"
                            gaps = line.split("=")[1].strip().split(",")[0] if "=" in line else ""
                            gaps = line.split("=")[1].strip().split(",")[0]
                        elif "Strand =" in line:
                            strand = line.split("=")[1].strip()
                    summary_data.append([fasta_file, score, expect, identities, gaps, strand])
            else:
                st.error(f"❌ No BLAST output found for {fasta_file}. Check your input sequences!")

        st.success("✅ BLAST alignment completed!")

        # 🔹 Step 1: Create a ZIP file with all BLAST result .txt files
        zip_path = os.path.join(blast_output_dir, "BLAST_Results.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for txt_file in os.listdir(blast_output_dir):
                if txt_file.endswith(".txt"):
                    zipf.write(os.path.join(blast_output_dir, txt_file), arcname=txt_file)

        st.success("✅ BLAST alignment files added to ZIP!")

        # 🔹 Step 2: Provide a download button for the ZIP file
        with open(zip_path, "rb") as zip_file:
            st.download_button(
                label="📥 Download BLAST Alignments (ZIP)",
                data=zip_file,
                file_name="BLAST_Results.zip",
                mime="application/zip"
            )

        # 🔹 Step 3: Generate Excel summary with BLAST metrics
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

        # 🔹 Step 4: Provide a download link for the Excel summary
        with open(excel_summary_file, "rb") as f:
            st.download_button(
                label="📥 Download BLAST Summary",
                data=f,
                file_name="BLAST_Summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
