import streamlit as st
import pandas as pd
import re
from io import BytesIO


# Define function to process SQL query and generate mappings
def generate_column_mappings(sql_query):
    # Define patterns to extract schema, table, and columns
    target_view_pattern = re.compile(r"REPLACE\s+VIEW\s+(\w+\.\w+)\s+AS", re.IGNORECASE)
    column_pattern = re.compile(r"\s*(\w+)\.(\w+)\s*(?:AS\s+(\w+))?", re.IGNORECASE)
    source_table_pattern = re.compile(r"FROM\s+(\w+\.\w+)\s+(\w+)", re.IGNORECASE)
    join_table_pattern = re.compile(r"JOIN\s+(\w+\.\w+)\s+(\w+)", re.IGNORECASE)

    # Function to extract transformation/mapping for a column
    def extract_column_transformation(sql_query, alias_col):
        transformation_pattern = re.compile(
            rf"(?P<transformation>CASE\s+WHEN\s+.*?\s+END|[A-Z]+\([^\)]*\))\s+AS\s+{alias_col}",
            re.IGNORECASE | re.DOTALL)
        match = transformation_pattern.search(sql_query)
        return match.group("transformation") if match else "1:1 Mapping"

    # Extract target view (schema and table)
    target_view_match = target_view_pattern.search(sql_query)
    target_schema, target_table = target_view_match.group(1).split(".")

    # Extract source tables and aliases
    source_tables = {}
    for match in re.findall(source_table_pattern, sql_query) + re.findall(join_table_pattern, sql_query):
        source_tables[match[1]] = match[0]  # alias as key, schema.table as value

    # Extract columns and their mappings
    mappings = []
    for match in re.findall(column_pattern, sql_query):
        alias, source_col, alias_col = match
        source_schema_table = source_tables.get(alias)
        if source_schema_table:
            source_schema, source_table = source_schema_table.split(".")
            alias_col = alias_col or source_col
            transformation_mapping = extract_column_transformation(sql_query, alias_col)
            mappings.append({
                "Target Schema": target_schema,
                "Target Table": target_table,
                "Target Column": alias_col,
                "Source Schema": source_schema,
                "Source Table": source_table,
                "Source Column": source_col,
                "Transformation / Mapping": transformation_mapping
            })
        else:
            st.warning(f"Alias '{alias}' not found in source tables.")

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

            # Convert mappings to DataFrame
            df = pd.DataFrame(mappings)

            # Show DataFrame in Streamlit
            st.dataframe(df)

            # Create an in-memory Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)

            # Set the buffer position to the beginning
            output.seek(0)

            # Button to download the DataFrame as Excel
            st.download_button(
                label="Download as Excel",
                data=output,
                file_name="column_mapping.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Please enter a SQL query.")


if __name__ == "__main__":
    main()
