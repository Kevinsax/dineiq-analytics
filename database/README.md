# database/

DineIQ Analytics does not use a database in this submission. All pipeline
output is stored as Parquet/CSV files under parquet_data/ and models/, read
directly by the Streamlit application in src/. This is documented as a known
limitation in the Project Report (reports/DineIQ_Project_Report.docx,
Section 38) -- a production version of this system would move these outputs
into a proper database (e.g. PostgreSQL) to support concurrent access,
versioning, and an audit trail, none of which flat files provide.
