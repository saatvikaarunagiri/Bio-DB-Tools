#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template
import pymysql
import json
from collections import Counter

application = Flask(__name__)
app = application

def get_db_connection():
    try:
        return pymysql.connect(
            host='myhostname',
            user='myusername',
            password='mypassword',
            db='mydb',
            port=-,
            charset='-',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None
@app.route('/network', methods=['GET'])
def index():
    # Get all diseases for dropdown
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
    
    return render_template('ppi_network.html', diseases=diseases)

@app.route('/get_ppi_data', methods=['GET'])
def get_ppi_data():
    disease = request.args.get('disease')
    if not disease:
        return jsonify({"status": "error", "message": "Disease not provided"}), 400

    max_proteins = int(request.args.get('max_proteins', 25))
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
  # Get disease description
        cursor.execute("SELECT Description FROM Disease2 WHERE Name = %s", (disease,))
        desc_row = cursor.fetchone()
        description = desc_row['Description'] if desc_row else None
        
        # Get all PPIs for this disease
        query = """
            SELECT 
                p1.Protein_ID AS source_id,
                p1.name AS source_name,
                p1.Gene_ID AS source_gene,
                p2.Protein_ID AS target_id,
                p2.name AS target_name,
                p2.Gene_ID AS target_gene,
                ppi.Experimental_system_type AS interaction_type,
                ppi.Throughput
            FROM 
                Protein_Interactions ppi
            JOIN Proteins p1 ON ppi.Protein_A_id = p1.Protein_ID
            JOIN Proteins p2 ON ppi.Protein_B_id = p2.Protein_ID
            JOIN Disease2 d ON ppi.Disease_id = d.Disease_id
            WHERE d.Name = %s
        """
        cursor.execute(query, (disease,))
        all_interactions = cursor.fetchall()
        
        # Count protein interactions to find the most connected ones
        protein_counts = Counter()
        for interaction in all_interactions:
            protein_counts[interaction['source_id']] += 1
            protein_counts[interaction['target_id']] += 1
        
        # Get the top N most connected proteins
        top_proteins = [protein_id for protein_id, count in protein_counts.most_common(max_proteins)]
        
        # Filter interactions to only include those involving top proteins
        filtered_interactions = []
        nodes = {}  # To keep track of unique nodes
        
  for interaction in all_interactions:
            source_id = interaction['source_id']
            target_id = interaction['target_id']
            
            # Only include interactions where at least one protein is in the top list
            if source_id in top_proteins or target_id in top_proteins:
                # Add source and target to nodes dictionary if not already there
                if source_id not in nodes:
                    nodes[source_id] = {
                        'id': source_id,
                        'name': interaction['source_name'],
                        'gene': interaction['source_gene'],
                        'connections': protein_counts[source_id]
                    }
                
               	if target_id not in nodes:
                    nodes[target_id] = {
                        'id': target_id,
                        'name': interaction['target_name'],
                        'gene': interaction['target_gene'],
                        'connections': protein_counts[target_id]
                    }
                
                # Add the interaction
                filtered_interactions.append({
                    'source': source_id,
                    'target': target_id,
                    'type': interaction['interaction_type'],
                    'throughput': interaction['Throughput'],
                    'value': 1  # Adding default value for link thickness
                })
        
        # Prepare final network data
        network_data = {
            'nodes': list(nodes.values()),
            'links': filtered_interactions,
            'description': description,
            'totalInteractions': len(all_interactions),
            'filteredInteractions': len(filtered_interactions),
            'totalProteins': len(protein_counts),
            'filteredProteins': len(nodes)
        }
  return jsonify({"status": "success", "data": network_data})
    except Exception as e:
        print(f"Error processing data: {e}")  # Add logging for debugging
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
