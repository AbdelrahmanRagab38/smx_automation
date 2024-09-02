import re
import pandas as pd
from io import BytesIO
import streamlit as st

def extract_schema_table(query, keyword):
    pattern = re.compile(rf"{keyword}\s+(\w+)\.(\w+)", re.IGNORECASE)
    match = pattern.search(query)
    return match.group(1), match.group(2) if match else (None, None)

def generate_column_mappings(sql_query):
    # Patterns to extract various parts of the query
    target_view_pattern = re.compile(r"REPLACE\s+VIEW\s+(\w+\.\w+)\s+AS", re.IGNORECASE)
    source_table_pattern = re.compile(r"FROM\s+(\w+\.\w+)", re.IGNORECASE)
    join_table_pattern = re.compile(r"JOIN\s+(\w+\.\w+)", re.IGNORECASE)
    transformation_pattern = re.compile(r"(?P<transformation>CASE\s+WHEN\s+.*?END|[A-Z]+\([^\)]*\))\s+AS\s+(?P<alias_col>\w+)", re.IGNORECASE | re.DOTALL)
    column_pattern = re.compile(r"\s*(\w+)\.(\w+)\s*(?:AS\s+(\w+))?", re.IGNORECASE)

    # Extract target view
    target_view_match = target_view_pattern.search(sql_query)
    if not target_view_match:
        st.error("Target view not found in the query.")
        return []
    target_schema, target_table = target_view_match.group(1).split(".")

    # Extract source table and schema
    source_schema, source_table = extract_schema_table(sql_query, "FROM")
    if not source_schema:
        source_schema, source_table = extract_schema_table(sql_query, "JOIN")

    if not source_schema:
        source_schema = "Unknown"
        source_table = "Unknown"

    # List of keywords to ignore
    ignore_keywords = ['for', 'replace', 'view', 'locking', 'row', 'select', 'case', 'when', 'in', 'then', 'else', 'distinct', 'AS', 'from', 'group', 'by']

    # Extract columns and transformations
    mappings = []
    for match in re.finditer(transformation_pattern, sql_query):
        transformation = match.group("transformation").strip()
        alias_col = match.group("alias_col").strip()

        # Skip if the alias column is a keyword to ignore
        if alias_col.lower() in ignore_keywords:
            continue

        mappings.append({
            "Target Schema": target_schema,
            "Target Table": target_table,
            "Target Column": alias_col,
            "Source Schema": source_schema,
            "Source Table": source_table,
            "Source Column": None,
            "Transformation / Mapping": transformation
        })

    # Extract plain columns that are not part of a transformation
    for match in re.finditer(column_pattern, sql_query):
        source_col = match.group(1).strip()
        alias_col = match.group(3).strip() if match.group(3) else source_col

        # Skip columns already mapped by transformations
        if any(m['Target Column'] == alias_col for m in mappings):
            continue

        mappings.append({
            "Target Schema": target_schema,
            "Target Table": target_table,
            "Target Column": alias_col,
            "Source Schema": source_schema,
            "Source Table": source_table,
            "Source Column": source_col,
            "Transformation / Mapping": "1:1 Mapping"
        })

    return mappings

# Streamlit app
def main():
    st.markdown("<h1 style='text-align: center; color: green;'>Qeema Tools</h1>", unsafe_allow_html=True)
    st.title("SQL to Excel Mapping Generator")

    # Text area for SQL query input
    sql_query = st.text_area("Enter your SQL query here:", height=300)

    if st.button("Generate Mapping"):
        if sql_query.strip():
            # Process the SQL query and generate mappings
            mappings = generate_column_mappings(sql_query)

            if mappings:
                df = pd.DataFrame(mappings)
                st.dataframe(df)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                output.seek(0)

                st.download_button(
                    label="Download as Excel",
                    data=output,
                    file_name="column_mapping.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("No mappings were found.")
        else:
            st.warning("Please enter a SQL query.")

if __name__ == "__main__":
    main()
