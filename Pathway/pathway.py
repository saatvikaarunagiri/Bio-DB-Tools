from flask import Flask, render_template, request, send_file
import pymysql
import pandas as pd
import io

app = Flask(__name__)

def get_db_connection():
    return pymysql.connect(
        host='myhostname',
        user='myusername',
        password='mypassword',
        db='mydb',
        port=-,
        charset='-',
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    gene_info = None
    pathway_results = []
    function_results = []
    error = None
    query_input = ""

    if request.method == 'POST':
        query_input = request.form.get('gene_input', '').strip()

        if not query_input:
            error = "Please enter a gene symbol or ENSEMBL ID."
        else:
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    # Convert input to uppercase for consistent matching
                    query_upper = query_input.upper()

                    # Get gene info
                    cursor.execute("""
                        SELECT Gene_ID, Symbol, Description, Start, End
                        FROM Gene
                        WHERE UPPER(Gene_ID) = %s OR UPPER(Symbol) = %s
                    """, (query_upper, query_upper))
                    gene_info = cursor.fetchone()

                    # Fallback: attempt loose symbol match
                    if not gene_info:
                        cursor.execute("""
                            SELECT Gene_ID, Symbol, Description, Start, End
                            FROM Gene
                            WHERE Symbol LIKE %s
                        """, (f"%{query_input}%",))
                        gene_info = cursor.fetchone()

                    if not gene_info:
                        error = f"No gene found for '{query_input}'. Please check your input."
                    else:
                        gene_id = gene_info['Gene_ID']
                        gene_info['Length'] = f"{int(gene_info['End']) - int(gene_info['Start'])} bp"

                        # Get pathways
                        cursor.execute("""
                            SELECT DISTINCT p.Pathway_ID, p.Name AS Pathway_Name
                            FROM Pathway_Gene pg
                            JOIN Pathway p ON pg.Pathway_ID = p.Pathway_ID
                            WHERE pg.Gene_ID = %s
                        """, (gene_id,))
                        pathway_results = cursor.fetchall()

                        # Get molecular functions
                        cursor.execute("""
                            SELECT DISTINCT gterm.go_id AS GO_ID, gterm.go_name AS Molecular_Function
                            FROM Gene_GO_annotation gga
                            JOIN GO_terms gterm ON gga.go_id = gterm.go_id
                            WHERE gga.Gene_ID = %s AND gterm.go_type = 'MF'
                        """, (gene_id,))
                        function_results = cursor.fetchall()
            except Exception as e:
                error = f"Database error: {e}"
            finally:
                conn.close()

    return render_template(
        'saneeya_finalproj.html',
        gene_info=gene_info,
        pathway_results=pathway_results,
        function_results=function_results,
        query_input=query_input,
        error=error
    )

@app.route('/download', methods=['POST'])
def download():
    format = request.form.get('format')
    query_input = request.form.get('query_input', '').strip()
    table_type = request.form.get('table_type')

    results = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query_upper = query_input.upper()
            cursor.execute("SELECT Gene_ID FROM Gene WHERE UPPER(Gene_ID) = %s OR UPPER(Symbol) = %s", (query_upper, query_upper))
            row = cursor.fetchone()

            if not row:
                cursor.execute("SELECT Gene_ID FROM Gene WHERE Symbol LIKE %s", (f"%{query_input}%",))
                row = cursor.fetchone()

            if not row:
                return f"No gene found for '{query_input}'."
            gene_id = row['Gene_ID']

            if table_type == 'pathway':
                cursor.execute("""
                    SELECT DISTINCT p.Pathway_ID, p.Name AS Pathway_Name
                    FROM Pathway_Gene pg
                    JOIN Pathway p ON pg.Pathway_ID = p.Pathway_ID
                    WHERE pg.Gene_ID = %s
                """, (gene_id,))
            elif table_type == 'function':
                cursor.execute("""
                    SELECT DISTINCT gterm.go_id AS GO_ID, gterm.go_name AS Molecular_Function
                    FROM Gene_GO_annotation gga
                    JOIN GO_terms gterm ON gga.go_id = gterm.go_id
                    WHERE gga.Gene_ID = %s AND gterm.go_type = 'MF'
                """, (gene_id,))
            results = cursor.fetchall()
    finally:
        conn.close()

    df = pd.DataFrame(results)
    file_buffer = io.StringIO()
    if format == 'tsv':
        df.to_csv(file_buffer, sep='\t', index=False)
        mime = 'text/tab-separated-values'
        ext = 'tsv'
    else:
        df.to_csv(file_buffer, index=False)
        mime = 'text/csv'
        ext = 'csv'

    file_buffer.seek(0)
    return send_file(io.BytesIO(file_buffer.getvalue().encode()), mimetype=mime,
                     as_attachment=True, download_name=f'{table_type}_table.{ext}')

application = app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
