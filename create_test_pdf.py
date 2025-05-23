#!/usr/bin/env python3

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    # Create a simple PDF for testing
    filename = 'test_success_notification.pdf'
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, 'Success Notification Test Document')
    c.drawString(100, 730, 'This document will test our success notification system.')
    c.drawString(100, 710, 'Pipeline should complete successfully and send notifications.')
    c.drawString(100, 690, 'Document contains simple text for embedding generation.')
    c.drawString(100, 670, 'We expect to see a SUCCESS notification in SQS.')
    c.drawString(100, 650, 'The notification should include chunk count and processing time.')
    c.save()
    print(f'✅ Created {filename}')
    
except ImportError:
    print("❌ reportlab not available. Creating a minimal PDF manually...")
    
    # Create a very basic PDF manually
    pdf_content = """%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
  /Font <<
    /F1 5 0 R
  >>
>>
>>
endobj

4 0 obj
<<
/Length 200
>>
stream
BT
/F1 12 Tf
50 750 Td
(Success Notification Test Document) Tj
0 -20 Td
(This document will test our success notification system.) Tj
0 -20 Td
(Pipeline should complete successfully and send notifications.) Tj
0 -20 Td
(We expect to see a SUCCESS notification in SQS.) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000103 00000 n 
0000000229 00000 n 
0000000480 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
547
%%EOF"""
    
    with open('test_success_notification.pdf', 'w') as f:
        f.write(pdf_content)
    print('✅ Created test_success_notification.pdf manually') 