from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
import pdfkit  # You'll need to install this: pip install pdfkit

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vip_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/passes'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Database Models
class VipGuest(db.Model):
    __tablename__ = 'vip_guests'
    
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(20), unique=True, nullable=False)
    pass_type = db.Column(db.String(10), nullable=False)  # 'VIP' or 'VVIP'
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    designation = db.Column(db.String(100))
    recommended_by = db.Column(db.String(100))
    car_number = db.Column(db.String(20))
    contact_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    accompanying_persons = db.relationship('AccompanyingPerson', backref='vip_guest', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<VipGuest {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'unique_id': self.unique_id,
            'pass_type': self.pass_type,
            'name': self.name,
            'gender': self.gender,
            'designation': self.designation,
            'recommended_by': self.recommended_by,
            'car_number': self.car_number,
            'contact_number': self.contact_number,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'accompanying_persons': [person.to_dict() for person in self.accompanying_persons]
        }

class AccompanyingPerson(db.Model):
    __tablename__ = 'accompanying_persons'
    
    id = db.Column(db.Integer, primary_key=True)
    vip_guest_id = db.Column(db.Integer, db.ForeignKey('vip_guests.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<AccompanyingPerson {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'vip_guest_id': self.vip_guest_id,
            'name': self.name,
            'gender': self.gender,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# Functions for pass generation and unique ID management
def get_next_unique_id():
    """Generate the next available unique ID"""
    last_guest = VipGuest.query.order_by(VipGuest.unique_id.desc()).first()
    
    if not last_guest:
        return "JMU-2024-1000"
    
    # Extract the numeric part of the ID
    try:
        id_parts = last_guest.unique_id.split('-')
        if len(id_parts) >= 3:
            num_part = int(id_parts[-1])
            new_id = f"JMU-2024-{num_part + 1}"
            return new_id
    except:
        pass
    
    # Fallback to default if something goes wrong
    return "JMU-2024-1000"

def generate_personal_pass_html(guest, is_accompanying_person=False, gender=None):
    """Generate HTML for personal pass"""
    is_vip = guest.pass_type == "VIP"
    bg_color = "#6BC45A" if is_vip else "#FF8800"  # Green for VIP, Orange for VVIP
    title_text = "VIP" if is_vip else "VVIP"
    
    # Determine gender text
    if is_accompanying_person:
        gender_text = "GENTS" if gender == "Male" else "LADIES"
    else:
        gender_text = "GENTS" if guest.gender == "Male" else "LADIES"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_text} Pass - {guest.name}</title>
    <style>
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
        .pass {{ width: 400px; margin: 0 auto; background-color: {bg_color}; border: 2px solid #000; position: relative; overflow: hidden; }}
        .pass-header {{ display: flex; background-color: white; border-bottom: 2px solid #000; padding: 10px; }}
        .logo {{ width: 50px; height: 50px; background-color: black; color: white; font-weight: bold; display: flex; justify-content: center; align-items: center; margin-right: 10px; border: 2px solid white; }}
        .header-text {{ flex: 1; }}
        .header-text h1 {{ font-size: 14px; font-weight: bold; line-height: 1.2; margin: 0; }}
        .serial {{ text-align: center; padding: 5px 0; font-weight: bold; }}
        .pass-type {{ text-align: center; margin: 10px auto; width: 120px; background-color: white; border: 2px solid red; padding: 5px; font-size: 24px; font-weight: bold; }}
        .date {{ font-weight: bold; text-decoration: underline; margin: 10px; }}
        .name {{ margin: 10px; font-size: 18px; }}
        .notes {{ margin: 10px; font-size: 12px; }}
        .notes ol {{ margin-left: 20px; }}
        .signature {{ display: flex; justify-content: flex-end; align-items: flex-end; height: 40px; margin: 0 10px 5px 0; }}
        .watermark {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; transform: rotate(-30deg); opacity: 0.1; pointer-events: none; z-index: 1; }}
        .watermark-text {{ font-size: 100px; font-weight: bold; white-space: nowrap; }}
    </style>
</head>
<body>
    <div class="pass">
        <div class="watermark">
            <div class="watermark-text">RSSB</div>
        </div>
        <div class="pass-header">
            <div class="logo">RS<br>SB</div>
            <div class="header-text">
                <h1>RADHA SOAMI SATSANG BEAS, JAMMU<br>SATSANG PROGRAMME 6<sup>th</sup> & 7<sup>th</sup> April, 2024</h1>
            </div>
        </div>
        <div class="serial">S.NO: {guest.unique_id}</div>
        <div class="pass-type">{gender_text}</div>
        <div class="date">6th April 2024 (SATURDAY)</div>
        <div class="name">{guest.name if not is_accompanying_person else is_accompanying_person}</div>
        <div class="date">7th April 2024 (SUNDAY)</div>
        <div class="notes">
            <div>NOTES:</div>
            <ol>
                <li>Please bring your ID card along with this pass.</li>
                <li>No electronic devices, mobile phones, smart watch, arms/weapons allowed.</li>
                <li>This pass is non-transferable.</li>
                <li>Incase of any need, please contact at 8082039255.</li>
                <li>Entry Closes: 9:00 AM  Satsang time: 9:30 AM</li>
            </ol>
        </div>
        <div class="signature">Auth. Signatory</div>
    </div>
</body>
</html>"""
    
    return html

def generate_car_pass_html(guest):
    """Generate HTML for car pass"""
    is_vip = guest.pass_type == "VIP"
    bg_color = "#6BC45A" if is_vip else "#FFCC00"  # Green for VIP, Yellow for VVIP
    title_text = "VIP" if is_vip else "VVIP"
    car_number_color = "blue" if is_vip else "red"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_text} Car Pass - {guest.name}</title>
    <style>
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
        .car-pass {{ background-color: {bg_color}; width: 600px; margin: 0 auto; border: 2px solid #000; position: relative; }}
        .car-header {{ background-color: white; text-align: center; padding: 10px; display: flex; justify-content: center; align-items: center; border-bottom: 2px solid black; }}
        .logo {{ width: 50px; height: 50px; background-color: black; color: white; font-weight: bold; display: flex; justify-content: center; align-items: center; margin-right: 10px; border: 2px solid white; }}
        .car-header-text h1 {{ font-size: 16px; font-weight: bold; line-height: 1.2; margin: 0; }}
        .car-content {{ padding: 20px; position: relative; }}
        .car-serial {{ position: absolute; top: 10px; left: 10px; font-weight: bold; }}
        .car-image {{ width: 300px; margin: 30px auto; display: block; }}
        .car-number {{ text-align: center; color: {car_number_color}; font-weight: bold; font-size: 36px; margin-top: -20px; margin-bottom: 30px; }}
        .car-footer {{ background-color: white; padding: 10px; text-align: center; font-weight: bold; border-top: 2px solid black; }}
        .signature {{ display: flex; justify-content: flex-end; align-items: flex-end; height: 40px; margin: 10px 10px 5px 0; }}
        .watermark {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; transform: rotate(-30deg); opacity: 0.1; pointer-events: none; z-index: 1; }}
        .watermark-text {{ font-size: 100px; font-weight: bold; white-space: nowrap; }}
    </style>
</head>
<body>
    <div class="car-pass">
        <div class="watermark">
            <div class="watermark-text">RSSB</div>
        </div>
        <div class="car-header">
            <div class="logo">RS<br>SB</div>
            <div class="car-header-text">
                <h1>RADHA SOAMI SATSANG BEAS, JAMMU<br>SATSANG PROGRAMME 6<sup>th</sup> & 7<sup>th</sup> April, 2024</h1>
            </div>
        </div>
        <div class="car-content">
            <div class="car-serial">SNO: {guest.unique_id}</div>
            <svg class="car-image" viewBox="0 0 400 150" xmlns="http://www.w3.org/2000/svg">
                <path d="M50,100 C70,60 100,40 180,40 L220,40 C300,40 330,60 350,100 L50,100 Z" fill="white" stroke="black" stroke-width="4"/>
                <line x1="180" y1="40" x2="180" y2="60" stroke="black" stroke-width="4"/>
                <line x1="220" y1="40" x2="220" y2="60" stroke="black" stroke-width="4"/>
                <circle cx="100" cy="100" r="25" fill="white" stroke="black" stroke-width="4"/>
                <circle cx="100" cy="100" r="15" fill="white" stroke="black" stroke-width="4"/>
                <circle cx="300" cy="100" r="25" fill="white" stroke="black" stroke-width="4"/>
                <circle cx="300" cy="100" r="15" fill="white" stroke="black" stroke-width="4"/>
            </svg>
            <div class="car-number">P - 2024</div>
            <div class="signature">Auth. Signatory</div>
        </div>
        <div class="car-footer">THIS CAR STICKER IS TO BE PASTED ON WINDSHIELD</div>
    </div>
</body>
</html>"""
    
    return html

# Routes
@app.route('/')
def index():
    return render_template('index.html', next_id=get_next_unique_id())

@app.route('/api/get_next_id', methods=['GET'])
def api_next_id():
    return jsonify({'unique_id': get_next_unique_id()})

@app.route('/generate_pass', methods=['POST'])
def generate_pass():
    try:
        # Extract form data
        pass_type = request.form.get('passType')
        unique_id = request.form.get('uniqueId')
        guest_name = request.form.get('guestName')
        gender = request.form.get('gender')
        designation = request.form.get('designation')
        recommended_by = request.form.get('recommendedBy')
        car_number = request.form.get('carNumber')
        contact_number = request.form.get('contactNumber')
        
        # Create new VIP guest
        new_guest = VipGuest(
            unique_id=unique_id,
            pass_type=pass_type,
            name=guest_name,
            gender=gender,
            designation=designation,
            recommended_by=recommended_by,
            car_number=car_number,
            contact_number=contact_number
        )
        
        # Add accompanying persons if any
        person_names = request.form.getlist('personName[]')
        person_genders = request.form.getlist('personGender[]')
        
        for i in range(len(person_names)):
            if i < len(person_genders) and person_names[i]:
                person = AccompanyingPerson(
                    name=person_names[i],
                    gender=person_genders[i]
                )
                new_guest.accompanying_persons.append(person)
        
        # Save to database
        db.session.add(new_guest)
        db.session.commit()
        
        # Generate personal pass HTML for the main guest
        personal_pass_html = generate_personal_pass_html(new_guest)
        
        # Save the HTML to a file
        personal_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_personal.html")
        with open(personal_pass_file, 'w') as f:
            f.write(personal_pass_html)
        
        # Generate accompanying person passes if needed
        for i, person in enumerate(new_guest.accompanying_persons):
            person_pass_html = generate_personal_pass_html(new_guest, is_accompanying_person=person.name, gender=person.gender)
            person_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_person_{i+1}.html")
            with open(person_pass_file, 'w') as f:
                f.write(person_pass_html)
        
        # Generate car pass if car number is provided
        if car_number:
            car_pass_html = generate_car_pass_html(new_guest)
            car_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_car.html")
            with open(car_pass_file, 'w') as f:
                f.write(car_pass_html)
            
            # Optional: Convert to PDF if pdfkit is installed
            try:
                pdfkit.from_file(car_pass_file, os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_car.pdf"))
            except Exception as e:
                app.logger.error(f"PDF generation error: {str(e)}")
        
        # Try to convert personal passes to PDF
        try:
            pdfkit.from_file(personal_pass_file, os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_personal.pdf"))
        except Exception as e:
            app.logger.error(f"PDF generation error: {str(e)}")
        
        flash('Passes generated successfully!', 'success')
        return redirect(url_for('view_pass', unique_id=unique_id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating passes: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/view_pass/<unique_id>')
def view_pass(unique_id):
    guest = VipGuest.query.filter_by(unique_id=unique_id).first_or_404()
    
    # Get file paths
    personal_pass_file = f"/static/passes/{unique_id}_personal.html"
    car_pass_file = f"/static/passes/{unique_id}_car.html" if guest.car_number else None
    
    # Get accompanying person pass files
    accompanying_passes = []
    for i, person in enumerate(guest.accompanying_persons):
        accompanying_passes.append({
            'name': person.name,
            'file': f"/static/passes/{unique_id}_person_{i+1}.html"
        })
    
    return render_template('view_passes.html', 
                          guest=guest, 
                          personal_pass_file=personal_pass_file,
                          car_pass_file=car_pass_file,
                          accompanying_passes=accompanying_passes)

@app.route('/admin')
def admin_dashboard():
    guests = VipGuest.query.order_by(VipGuest.created_at.desc()).all()
    return render_template('admin.html', guests=guests)

@app.route('/edit_guest/<unique_id>')
def edit_guest(unique_id):
    guest = VipGuest.query.filter_by(unique_id=unique_id).first_or_404()
    person_count = len(guest.accompanying_persons) if hasattr(guest, 'accompanying_persons') and guest.accompanying_persons else 0
    return render_template('edit_guest.html', guest=guest, person_count=person_count)

@app.route('/update_guest/<unique_id>', methods=['POST'])
def update_guest(unique_id):
    try:
        guest = VipGuest.query.filter_by(unique_id=unique_id).first_or_404()
        
        # Update guest information
        guest.pass_type = request.form.get('passType')
        guest.name = request.form.get('guestName')
        guest.gender = request.form.get('gender')
        guest.designation = request.form.get('designation')
        guest.recommended_by = request.form.get('recommendedBy')
        guest.car_number = request.form.get('carNumber')
        guest.contact_number = request.form.get('contactNumber')
        
        # Handle accompanying persons
        person_ids = request.form.getlist('personId[]')
        person_names = request.form.getlist('personName[]')
        person_genders = request.form.getlist('personGender[]')
        
        # Update or add accompanying persons
        for i in range(len(person_ids)):
            if i < len(person_names) and i < len(person_genders):
                # New person
                if person_ids[i] == 'new':
                    if person_names[i].strip():  # Only add if name is not empty
                        new_person = AccompanyingPerson(
                            name=person_names[i],
                            gender=person_genders[i]
                        )
                        guest.accompanying_persons.append(new_person)
                # Existing person
                else:
                    person = AccompanyingPerson.query.get(int(person_ids[i]))
                    if person and person.vip_guest_id == guest.id:
                        person.name = person_names[i]
                        person.gender = person_genders[i]
        
        # Handle deleted persons
        delete_person_ids = request.form.getlist('deletePerson[]')
        for person_id in delete_person_ids:
            person = AccompanyingPerson.query.get(int(person_id))
            if person and person.vip_guest_id == guest.id:
                db.session.delete(person)
        
        # Save changes
        db.session.commit()
        
        # Regenerate passes
        regenerate_passes(guest)
        
        flash('Guest information updated successfully!', 'success')
        return redirect(url_for('view_pass', unique_id=guest.unique_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating guest: {str(e)}', 'error')
        return redirect(url_for('edit_guest', unique_id=unique_id))

@app.route('/delete_guest/<unique_id>', methods=['POST'])
def delete_guest(unique_id):
    try:
        guest = VipGuest.query.filter_by(unique_id=unique_id).first_or_404()
        
        # Delete pass files
        try:
            # Personal pass
            personal_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_personal.html")
            if os.path.exists(personal_pass_file):
                os.remove(personal_pass_file)
            
            personal_pass_pdf = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_personal.pdf")
            if os.path.exists(personal_pass_pdf):
                os.remove(personal_pass_pdf)
            
            # Car pass
            if guest.car_number:
                car_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_car.html")
                if os.path.exists(car_pass_file):
                    os.remove(car_pass_file)
                
                car_pass_pdf = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_car.pdf")
                if os.path.exists(car_pass_pdf):
                    os.remove(car_pass_pdf)
            
            # Accompanying persons passes
            for i in range(len(guest.accompanying_persons)):
                person_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_person_{i+1}.html")
                if os.path.exists(person_pass_file):
                    os.remove(person_pass_file)
                
                person_pass_pdf = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_person_{i+1}.pdf")
                if os.path.exists(person_pass_pdf):
                    os.remove(person_pass_pdf)
        except Exception as e:
            app.logger.error(f"Error deleting pass files: {str(e)}")
        
        # Delete database record
        db.session.delete(guest)
        db.session.commit()
        
        flash('Guest and all associated passes deleted successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting guest: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

def regenerate_passes(guest):
    """Regenerate all passes for a guest after update"""
    try:
        unique_id = guest.unique_id
        
        # Generate personal pass HTML for the main guest
        personal_pass_html = generate_personal_pass_html(guest)
        
        # Save the HTML to a file
        personal_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_personal.html")
        with open(personal_pass_file, 'w') as f:
            f.write(personal_pass_html)
        
        # Generate accompanying person passes if needed
        for i, person in enumerate(guest.accompanying_persons):
            person_pass_html = generate_personal_pass_html(guest, is_accompanying_person=person.name, gender=person.gender)
            person_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_person_{i+1}.html")
            with open(person_pass_file, 'w') as f:
                f.write(person_pass_html)
        
        # Generate car pass if car number is provided
        if guest.car_number:
            car_pass_html = generate_car_pass_html(guest)
            car_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_car.html")
            with open(car_pass_file, 'w') as f:
                f.write(car_pass_html)
            
            # Optional: Convert to PDF if pdfkit is installed
            try:
                pdfkit.from_file(car_pass_file, os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_car.pdf"))
            except Exception as e:
                app.logger.error(f"PDF generation error: {str(e)}")
        
        # Try to convert personal passes to PDF
        try:
            pdfkit.from_file(personal_pass_file, os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_personal.pdf"))
            
            # Convert accompanying person passes to PDF
            for i in range(len(guest.accompanying_persons)):
                person_pass_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_person_{i+1}.html")
                pdfkit.from_file(person_pass_file, os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_person_{i+1}.pdf"))
        except Exception as e:
            app.logger.error(f"PDF generation error: {str(e)}")
            
    except Exception as e:
        app.logger.error(f"Error regenerating passes: {str(e)}")

@app.route('/download/<unique_id>/<pass_type>')
def download_pass(unique_id, pass_type):
    if pass_type == 'personal':
        filename = f"{unique_id}_personal.pdf"
    elif pass_type == 'car':
        filename = f"{unique_id}_car.pdf"
    else:
        # For accompanying persons
        person_num = pass_type.split('_')[-1]
        filename = f"{unique_id}_person_{person_num}.pdf"
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        # Try HTML if PDF doesn't exist
        html_path = file_path.replace('.pdf', '.html')
        if os.path.exists(html_path):
            return send_file(html_path, as_attachment=True)
        else:
            flash('File not found', 'error')
            return redirect(url_for('index'))

@app.route('/api/guests', methods=['GET'])
def api_guests():
    guests = VipGuest.query.all()
    return jsonify([guest.to_dict() for guest in guests])

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)