from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder='templates')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')

# Form submission route
@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    message = request.form.get('message')

    # For now, just print to console (can be expanded later)
    print(f"Contact form submitted:\nName: {first_name} {last_name}\nEmail: {email}\nMessage: {message}")

    # Redirect back to home or show thank you page (optional)
    return redirect(url_for('home'))

if __name__ == '__main__':
         app.run(debug=True)

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/my/path/to/PPI_help.docx')
def download_PPI_doc():
    return send_from_directory('/var/www/html/my/path/to', 'PPI_help.docx')

@app.route('/my/path/to/Pathways_help.docx')
def download_pathways_doc():
    return send_from_directory('/var/www/html/my/path/to', 'Pathways_help.docx')

@app.route('/my/path/to/Pathways_help.docx')
def download_GO_Term_doc():
    return send_from_directory('/var/www/html/my/path/to', 'Pathways_help.docx')
