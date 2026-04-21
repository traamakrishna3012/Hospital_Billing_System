import docx

doc = docx.Document('d:/Freelance/Hospital Bill System/VAPT_ReAssessment_Update_April21.docx')
with open('vapt_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join([p.text for p in doc.paragraphs]))
