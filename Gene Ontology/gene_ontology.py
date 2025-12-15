#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template, Response
import pymysql
from flask_cors import CORS

application = Flask(__name__)
app = application
CORS(app)

def get_db_connection():
    try:
        return pymysql.connect(
            host='myhost',
            user='myusername',
            password='mypassword',
            db='mydb',
            port=myport,
            charset='-',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

@app.route('/', methods=['GET'])
def index():
    if request.args.get('disease'):
        return get_go_terms()
    
    conn = get_db_connection()
    diseases = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Name FROM Disease2 ORDER BY Name")
            disease_rows = cursor.fetchall()
            diseases = [row['Name'] for row in disease_rows]
        except Exception as e:
            print(f"Error fetching diseases: {e}")
        finally:
            conn.close()
    
    return render_template('query2.html', 
                         diseases=diseases,
                         selected_disease=request.args.get('disease', ''),
                         selected_go_type=request.args.get('go_type', 'All'))

def get_go_terms():
    disease = request.args.get('disease')
    go_type = request.args.get('go_type', 'All')
    entries_param = request.args.get('entries', '')
    limit = None if entries_param == 'all' else 200

    if not disease:
        return jsonify({"status": "error", "message": "Disease not provided", "data": []}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"status": "error", "message": "Database connection failed", "data": []}), 500

    try:
        cursor = conn.cursor()
        query = """
            SELECT DISTINCT 
                g.Symbol AS gene,
                gda.Global_score AS confidence_score,
                go.go_id AS go_id,
                go.go_name AS go_term,
                CASE go.go_type
                    WHEN 'BP' THEN 'Biological Process'
                    WHEN 'MF' THEN 'Molecular Function'
                    WHEN 'CC' THEN 'Cellular Component'
                    ELSE go.go_type
                END AS category
            FROM Disease2 d
            JOIN Gene_Disease_Association gda ON d.Disease_id = gda.Disease_id
            JOIN Gene g ON gda.Gene_id = g.Gene_ID
            JOIN Gene_GO_annotation ggo ON g.Gene_ID = ggo.Gene_ID
            JOIN GO_terms go ON ggo.go_id = go.go_id
            WHERE d.Name = %s
        """
        params = [disease]
        
        if go_type != 'All':
            query += " AND go.go_type = %s"
            params.append(go_type)

        query += " ORDER BY gda.Global_score DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": rows,
            "disease": disease,
            "go_type": go_type
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": []}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
