#!/usr/bin/env python3
"""
Clinical Case Study PDF Generator
Generates a realistic medical case study document for testing purposes.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import datetime

def create_clinical_case_pdf():
    """Generate a comprehensive clinical case study PDF"""
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        "small_clinical_case_study.pdf",
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.darkred
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Story elements
    story = []
    
    # Title
    story.append(Paragraph("COMPREHENSIVE CLINICAL CASE STUDY", title_style))
    story.append(Paragraph("Acute Kidney Injury with Pneumonia Complication", styles['Heading3']))
    story.append(Spacer(1, 20))
    
    # Patient Information
    story.append(Paragraph("PATIENT INFORMATION", heading_style))
    
    patient_data = [
        ['Patient ID:', 'CS-2024-001'],
        ['Name:', 'Mr. Theodore Martinez'],
        ['Age:', '77 years'],
        ['Gender:', 'Male'],
        ['Date of Admission:', 'March 15, 2024'],
        ['Hospital:', 'Metropolitan Medical Center'],
        ['Attending Physician:', 'Dr. Sarah Chen, MD'],
        ['Department:', 'Internal Medicine']
    ]
    
    patient_table = Table(patient_data, colWidths=[2*inch, 3*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # Chief Complaint
    story.append(Paragraph("CHIEF COMPLAINT", heading_style))
    story.append(Paragraph(
        "77-year-old male presenting with acute kidney injury (AKI), fever, productive cough, "
        "and respiratory distress following 3-day illness progression.",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # History of Present Illness
    story.append(Paragraph("HISTORY OF PRESENT ILLNESS", heading_style))
    story.append(Paragraph(
        "Mr. Martinez was in his usual state of health until 3 days prior to admission when he "
        "experienced the sudden onset of a shaking chill followed by high fever (temperature "
        "reaching 38.6°C). Subsequently, he developed a productive cough with rusty-colored "
        "sputum, progressive fatigue, and lethargy. His symptoms have progressively worsened "
        "over the past 72 hours, with persistent fever, increased cough frequency, and the "
        "development of shortness of breath.",
        normal_style
    ))
    story.append(Paragraph(
        "The patient reports decreased oral intake due to poor appetite and nausea. He denies "
        "chest pain, but acknowledges mild dyspnea on exertion that has worsened to dyspnea "
        "at rest. He has noticed decreased urine output over the past 24 hours. No recent "
        "travel, sick contacts, or changes in medications prior to illness onset.",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # Past Medical History
    story.append(Paragraph("PAST MEDICAL HISTORY", heading_style))
    story.append(Paragraph(
        "1. Hypertension - well-controlled on current regimen for past 8 years<br/>"
        "2. Prostate adenocarcinoma - diagnosed 5 years ago, treated with external beam "
        "radiation therapy, currently in remission<br/>"
        "3. Osteoarthritis - primarily affecting knees and lower back<br/>"
        "4. Benign prostatic hyperplasia - managed conservatively<br/>"
        "5. History of kidney stones - last episode 3 years ago",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # Medications
    story.append(Paragraph("CURRENT MEDICATIONS", heading_style))
    story.append(Paragraph(
        "1. Hydrochlorothiazide 25 mg daily<br/>"
        "2. Lisinopril 10 mg daily<br/>"
        "3. Ibuprofen 400 mg as needed for arthritis pain<br/>"
        "4. Multivitamin daily<br/>"
        "5. Calcium carbonate 1000 mg twice daily",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # Social History
    story.append(Paragraph("SOCIAL HISTORY", heading_style))
    story.append(Paragraph(
        "Mr. Martinez is a retired construction foreman who lives with his spouse of 52 years. "
        "He has a 30 pack-year smoking history but currently smokes only 2-3 cigarettes per day. "
        "Alcohol consumption is minimal, approximately 1 drink per week. He denies illicit drug use. "
        "He remains active with gardening and light home maintenance activities.",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # Family History
    story.append(Paragraph("FAMILY HISTORY", heading_style))
    story.append(Paragraph(
        "Father: Died at age 82 from myocardial infarction, history of diabetes and hypertension<br/>"
        "Mother: Died at age 79 from stroke, history of atrial fibrillation<br/>"
        "Siblings: Two brothers, one with diabetes, one with prostate cancer<br/>"
        "Children: Three adult children, all healthy",
        normal_style
    ))
    
    # Physical Examination
    story.append(PageBreak())
    story.append(Paragraph("PHYSICAL EXAMINATION", heading_style))
    
    # Vital Signs
    vital_data = [
        ['Temperature:', '38.6°C (101.5°F)'],
        ['Blood Pressure:', '90/60 mmHg'],
        ['Heart Rate:', '110 bpm, regular'],
        ['Respiratory Rate:', '24 breaths/minute'],
        ['Oxygen Saturation:', '88% on room air'],
        ['Weight:', '82 kg (181 lbs)'],
        ['Height:', '175 cm (5\'9")'],
        ['BMI:', '26.8 kg/m²']
    ]
    
    vital_table = Table(vital_data, colWidths=[2*inch, 2.5*inch])
    vital_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.lightblue),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(vital_table)
    story.append(Spacer(1, 15))
    
    # System Review
    story.append(Paragraph("SYSTEM EXAMINATION", heading_style))
    story.append(Paragraph(
        "<b>General:</b> Elderly male appearing acutely ill, mildly dehydrated with dry mucous "
        "membranes. Alert and oriented x3 but appears fatigued.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>HEENT:</b> Normocephalic, atraumatic. PERRLA, EOMI. Dry mucous membranes, no "
        "oral lesions. Neck supple, no lymphadenopathy or thyromegaly.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Cardiovascular:</b> Tachycardic, regular rhythm. No murmurs, rubs, or gallops. "
        "Peripheral pulses present but weak. No peripheral edema.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Pulmonary:</b> Tachypneic with mild accessory muscle use. Decreased breath sounds "
        "at right lung base with coarse crackles. Dullness to percussion over right lower lobe.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Abdominal:</b> Soft, non-tender, non-distended. Normal bowel sounds. No "
        "hepatosplenomegaly or masses palpated.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Extremities:</b> No cyanosis, clubbing, or edema. Good range of motion despite "
        "mild arthritis changes in knees.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Neurological:</b> Alert and oriented x3. Cranial nerves II-XII intact. Motor "
        "strength 5/5 in all extremities. DTRs 2+ and symmetric.",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Laboratory Results
    story.append(Paragraph("LABORATORY RESULTS", heading_style))
    
    lab_data = [
        ['Test', 'Result', 'Reference Range'],
        ['White Blood Cell Count', '16,000/mcL', '4,500-11,000/mcL'],
        ['Neutrophils', '70%', '50-70%'],
        ['Bands', '20%', '0-5%'],
        ['Lymphocytes', '10%', '20-40%'],
        ['Hemoglobin', '10.2 g/dL', '13.5-17.5 g/dL'],
        ['Hematocrit', '32%', '41-53%'],
        ['MCV', '88 fL', '80-100 fL'],
        ['Sodium', '140 mEq/L', '136-145 mEq/L'],
        ['Potassium', '5.4 mEq/L', '3.5-5.1 mEq/L'],
        ['Chloride', '100 mEq/L', '98-107 mEq/L'],
        ['Bicarbonate', '19 mEq/L', '22-28 mEq/L'],
        ['BUN', '40 mg/dL', '7-20 mg/dL'],
        ['Creatinine', '3.8 mg/dL', '0.7-1.3 mg/dL'],
        ['Glucose', '102 mg/dL', '70-99 mg/dL'],
    ]
    
    lab_table = Table(lab_data, colWidths=[2.5*inch, 1.5*inch, 1.8*inch])
    lab_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(lab_table)
    story.append(Spacer(1, 15))
    
    # Urinalysis
    story.append(Paragraph("URINALYSIS", heading_style))
    
    urine_data = [
        ['Parameter', 'Result', 'Reference'],
        ['Specific Gravity', '1.010', '1.003-1.030'],
        ['Protein', 'Trace', 'Negative'],
        ['Glucose', 'Negative', 'Negative'],
        ['Blood', 'Negative', 'Negative'],
        ['Leukocyte Esterase', 'Negative', 'Negative'],
        ['RBC', '1/hpf', '0-2/hpf'],
        ['WBC', '1-2/hpf', '0-5/hpf'],
        ['Casts', 'Granular casts present', 'None'],
        ['Urine Sodium', '40 mEq/L', 'Variable'],
        ['FENa', '2.41%', '<1% (prerenal)'],
        ['FEurea', '53%', '<35% (prerenal)']
    ]
    
    urine_table = Table(urine_data, colWidths=[2.2*inch, 1.8*inch, 1.8*inch])
    urine_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightcoral),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(urine_table)
    
    # Imaging Studies
    story.append(PageBreak())
    story.append(Paragraph("IMAGING STUDIES", heading_style))
    story.append(Paragraph(
        "<b>Chest X-Ray:</b> Right lower lobe consolidation consistent with pneumonia. "
        "No pleural effusion or pneumothorax. Heart size normal.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Renal Ultrasound:</b> Normal kidney size and echogenicity bilaterally. "
        "No hydronephrosis, stones, or masses identified. Good cortical-medullary "
        "differentiation preserved.",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Assessment and Plan
    story.append(Paragraph("CLINICAL ASSESSMENT", heading_style))
    story.append(Paragraph(
        "<b>Primary Diagnoses:</b><br/>"
        "1. Acute Kidney Injury (AKI) - likely acute tubular necrosis secondary to sepsis and dehydration<br/>"
        "2. Community-acquired pneumonia - right lower lobe<br/>"
        "3. Sepsis secondary to pneumonia<br/>"
        "4. Dehydration",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Secondary Diagnoses:</b><br/>"
        "5. Acute on chronic kidney disease<br/>"
        "6. Hypertension<br/>"
        "7. History of prostate cancer - in remission<br/>"
        "8. Osteoarthritis",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Treatment Plan
    story.append(Paragraph("TREATMENT PLAN", heading_style))
    story.append(Paragraph(
        "<b>Immediate Management:</b><br/>"
        "• IV fluid resuscitation with normal saline 1-2 L bolus, then maintenance fluids<br/>"
        "• Empiric antibiotic therapy: Ceftriaxone 1g IV daily + Azithromycin 500mg daily<br/>"
        "• Oxygen supplementation to maintain SpO2 >92%<br/>"
        "• Monitor urine output with Foley catheter<br/>"
        "• Serial monitoring of renal function and electrolytes",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Supportive Care:</b><br/>"
        "• NPO initially, advance diet as tolerated<br/>"
        "• DVT prophylaxis with sequential compression devices<br/>"
        "• Hold nephrotoxic medications (ACE inhibitor, diuretics)<br/>"
        "• Pain management with acetaminophen (avoid NSAIDs)<br/>"
        "• Pulmonary toilet and incentive spirometry",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Clinical Course
    story.append(Paragraph("CLINICAL COURSE", heading_style))
    story.append(Paragraph(
        "<b>Hospital Day 1-3:</b> Patient responded well to IV antibiotics and fluid "
        "resuscitation. Blood pressure stabilized, fever curve downtrended. Repeat "
        "creatinine remained elevated at 3.8 mg/dL despite adequate hydration.",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Hospital Day 4-7:</b> Gradual improvement in respiratory symptoms. Patient "
        "began producing less sputum, oxygen requirements decreased. Creatinine began "
        "to trend downward to 2.8 mg/dL by day 5, and 2.0 mg/dL by discharge.",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Discharge Planning
    story.append(Paragraph("DISCHARGE PLANNING", heading_style))
    story.append(Paragraph(
        "<b>Discharge Medications:</b><br/>"
        "• Azithromycin 250mg daily x 3 more days<br/>"
        "• Resume Lisinopril 5mg daily (reduced dose)<br/>"
        "• Hold hydrochlorothiazide until nephrology follow-up<br/>"
        "• Acetaminophen 650mg q6h PRN pain (avoid NSAIDs)",
        normal_style
    ))
    story.append(Paragraph(
        "<b>Follow-up Care:</b><br/>"
        "• Primary care physician in 1 week<br/>"
        "• Nephrology consultation in 2 weeks<br/>"
        "• Repeat chest X-ray in 6 weeks<br/>"
        "• Monitor renal function in 3-5 days",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Complications
    story.append(Paragraph("POST-DISCHARGE COMPLICATIONS", heading_style))
    story.append(Paragraph(
        "Two weeks post-discharge, patient returned for follow-up with complaints of "
        "increased joint pain due to prolonged bed rest during hospitalization. He had "
        "been self-medicating with celecoxib (Celebrex) for osteoarthritis pain. "
        "Laboratory studies showed creatinine increased to 2.5 mg/dL. Patient was "
        "counseled to discontinue NSAID use immediately.",
        normal_style
    ))
    story.append(Paragraph(
        "Repeat laboratory studies 2 weeks after discontinuing celecoxib showed "
        "improvement in renal function with creatinine returning to 1.5 mg/dL, "
        "approaching his baseline of 1.4 mg/dL from one month prior to admission.",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Educational Points
    story.append(Paragraph("PATIENT EDUCATION POINTS", heading_style))
    story.append(Paragraph(
        "• Importance of medication compliance and avoiding nephrotoxic agents<br/>"
        "• Recognition of signs/symptoms requiring immediate medical attention<br/>"
        "• Proper hydration and infection prevention strategies<br/>"
        "• Safe pain management alternatives to NSAIDs<br/>"
        "• Regular monitoring of kidney function<br/>"
        "• Smoking cessation counseling provided",
        normal_style
    ))
    story.append(Spacer(1, 20))
    
    # Footer
    story.append(Paragraph(
        "This case demonstrates the complex interplay between acute illness, chronic "
        "conditions, and medication management in elderly patients. The development of "
        "AKI in the setting of pneumonia-induced sepsis, combined with the subsequent "
        "nephrotoxic injury from NSAID use, highlights the importance of careful "
        "medication reconciliation and patient education in preventing avoidable "
        "complications.",
        normal_style
    ))
    
    # Document metadata
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        f"Document prepared: {datetime.datetime.now().strftime('%B %d, %Y')}<br/>"
        "Case Study #: CS-2024-001<br/>"
        "Educational Use Only - Patient identifiers have been modified for privacy",
        styles['Normal']
    ))
    
    # Build the PDF
    doc.build(story)
    print("Clinical case study PDF generated successfully: small_clinical_case_study.pdf")

if __name__ == "__main__":
    create_clinical_case_pdf() 