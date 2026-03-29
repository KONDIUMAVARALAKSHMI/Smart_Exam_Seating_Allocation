from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from .models import Examallotment
from reportlab.platypus import PageBreak
from io import BytesIO
from reportlab.lib.units import mm
from django.http import HttpResponse
# adminapp/views.py  (or wherever build_attendance_table lives)
import os                       # ← add this line
from io import BytesIO
from django.conf import settings
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Image, Spacer, PageBreak
)
# … the rest of your imports


from adminapp.models import AddexamHall   
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


from datetime import datetime
from typing import List, Optional


from reportlab.platypus import (
    Paragraph, Table, TableStyle, Spacer, PageBreak
)

from reportlab.lib.styles import getSampleStyleSheet
from adminapp.models import AddexamHall, Room 



def hall_for_room(room_no: str) -> AddexamHall | None:
    """
    Return the AddexamHall instance whose rooms_list contains room_no.
    Assumes rooms_list is a comma-separated list like "103,104,105".
    """
    return (
        AddexamHall.objects
        .filter(rooms_list__regex=rf'(^|,){room_no}(,|$)')
        .first()
    )

def generate_examallotment_pdf(request):
    # Query data from the Examallotment table
    examallotments = Examallotment.objects.all()

    # Create a buffer to store PDF in memory
    buffer = BytesIO()

    # Create a PDF document with slightly adjusted margins
    pdf = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=72, bottomMargin=72)
    elements = []

    # Detect unique department codes from roll numbers instead of using examallotment.department directly
    dept_mapping = {
        "DS": "Data Science",
        "IT": "Information Technology",
        # Add more department codes if needed
    }

    # Extract dept_code from roll number pattern (assuming rollno is in Student_Id)
    dept_codes = sorted(set(
        exam.Student_Id[5:7]  # 6th & 7th characters in roll no (0-indexed)
        for exam in examallotments
    ))

    for dept_code in dept_codes:
        department_name = dept_mapping.get(dept_code, dept_code)

        # Add page break for each department after the first one
        if elements:
            elements.append(PageBreak())

        # Add logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'adlogo.png')
        logo = Image(logo_path, width=350, height=80)
        logo.hAlign = "CENTER"
        elements.append(logo)
        elements.append(Spacer(1, 6)) 

        # Add Seating Arrangement heading
        elements.append(Paragraph("<b>SEATING ARRANGEMENT</b>", getSampleStyleSheet()['Title']))
        elements.append(Spacer(1, 12))

        # Filter records for the current department code
        department_examallotments = examallotments.filter(Student_Id__icontains=dept_code)

        # Get starttime, date, venue
        starttime = department_examallotments.first().starttime
        date = department_examallotments.first().date
        venue = "BGB"

        # Exam date row
        body_text_style = getSampleStyleSheet()['BodyText']
        exam_timings_and_date = Table(
            [['', '', Paragraph(f"<b>Date:</b> {date.strftime('%d-%m-%Y')}", body_text_style)]],
            colWidths=[270, 100, 200]
        )
        exam_timings_and_date.setStyle(TableStyle([
            ('ALIGN', (2, 0), (2, 0), 'RIGHT')
        ]))
        elements.append(exam_timings_and_date)
        elements.append(Spacer(1, 6))

        # Venue row
        exam_venue = f"<b>Venue:</b> {venue}"
        elements.extend([
            Paragraph(exam_venue, body_text_style),
            Spacer(1, 18)
        ])

        # Department heading
        elements.append(Paragraph(f"<b>Department: {department_name}</b>", getSampleStyleSheet()['Title']))
        elements.append(Spacer(1, 12))

        # Group students by room
        room_data = {}
        for examallotment in department_examallotments:
            room_data.setdefault(examallotment.RoomNo, []).append(examallotment)

        # Prepare table data
        combined_data = [['S.No', 'Roll Numbers', 'Room No', 'Total']]
        serial_no = 1
        for room, room_examallotments in room_data.items():
            roll_numbers = [exam.Student_Id for exam in room_examallotments]
            total_count = len(room_examallotments)
            combined_data.append([
                serial_no,
                f"{min(roll_numbers)} to {max(roll_numbers)}",
                room,
                total_count
            ])
            serial_no += 1

        # Create table
        col_widths = [150, 150, 150, 100]
        table = Table(combined_data, colWidths=col_widths)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 18),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])
        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 36))

        # Footer with in-charge and HOD
        in_charge_and_hod_table = Table([
            [Paragraph("Exam Cell In Charge:", body_text_style), Spacer(1, 1), Paragraph("Head of the Department:", body_text_style)]
        ], colWidths=[200, 100, 200])
        in_charge_and_hod_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT')
        ]))
        elements.append(in_charge_and_hod_table)

    # Build PDF
    pdf.build(elements)

    # Return PDF as response
    pdf_content = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf_content, content_type="application/pdf")
    response['Content-Disposition'] = 'attachment; filename=examallotment.pdf'
    return response




def download_room_report(request):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=72,
        bottomMargin=72
    )
    elements = []

    # Every distinct room in the allotment table
    for room in (
        Examallotment.objects
        .values_list('RoomNo', flat=True)
        .distinct()
    ):
        room_data = Examallotment.objects.filter(RoomNo=room)
        if not room_data.exists():
            continue

        # Try to get the hall from the room number
        room_number_str = room.replace('Room', '').strip()
        hall = AddexamHall.objects.filter(rooms_list__icontains=room_number_str).first()

        elements.extend(get_room_elements(room_number_str, list(room_data), hall))
        elements.append(PageBreak())

    pdf.build(elements)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


def get_room_elements(room_number: str, room_data: list, hall: AddexamHall | None):
    styles = getSampleStyleSheet()
    elements = []

    # ── College title / logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'adlogo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=350, height=80)
        logo.hAlign = "CENTER"
        elements.append(logo)
        elements.append(Spacer(1, 6))

    # ── Header-left : venue & room
    left_table = Table([
        [Paragraph("<b>Venue:</b> BGB", styles['BodyText'])],
        [Paragraph(f"<b>Room Number:</b> {room_number}", styles['BodyText'])],
    ], hAlign='LEFT')

    # ── Header-right : date + subjects
    if hall:
        exam_date = hall.date.strftime('%d-%m-%Y') if hall.date else '—'
        sub1 = hall.subject1 or '—'
        sub2 = hall.subject2 or '—'
        students_per_bench = hall.students_per_bench or 2
    else:
        exam_date = sub1 = sub2 = '—'
        students_per_bench = 2  # fallback

    right_table = Table([
        [Paragraph(f"<b>Date:</b> {exam_date}", styles['BodyText'])],
        [Paragraph(f"<b>Subject 1:</b> {sub1}", styles['BodyText'])],
        [Paragraph(f"<b>Subject 2:</b> {sub2}", styles['BodyText'])],
    ], hAlign='RIGHT')

    header = Table([[left_table, right_table]], colWidths=[400, 150])
    header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements += [header, Spacer(1, 12)]

    # ── Roll-number grid
    elements.append(create_roll_number_grid(room_data, students_per_bench))
    elements.append(Spacer(1, 24))

    # ── Summary table
    summary = Table(
        [['Year', 'Branch', 'No. Registered', 'Presentees', 'Absentees'],
         ['', '', '', '', ''],
         ['', '', '', '', '']],
        colWidths=[100, 100, 120, 100, 100]
    )
    summary.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements += [summary, Spacer(1, 24)]

    # ── Signature table
    sig_table = Table(
        [["", "", "", ""],
         ["", "", "Invigilator 1 Signature", "Invigilator 2 Signature"]],
        colWidths=[50, 150, 150, 150]
    )
    sig_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (3, 1), 'CENTER'),
        ('LINEABOVE', (2, 0), (2, 0), 0.8, colors.black),
        ('LINEABOVE', (3, 0), (3, 0), 0.8, colors.black),
        ('TOPPADDING', (2, 0), (3, 0), 20),
    ]))
    elements.append(sig_table)

    return elements

    

def infer_students_per_bench(room_data):
    # Count the number of students assigned to each bench
    bench_students_count = {}
    for examallotment in room_data:
        bench_number = examallotment.BenchNo
        if bench_number not in bench_students_count:
            bench_students_count[bench_number] = 0
        bench_students_count[bench_number] += 1
    
    # Determine the most common number of students per bench
    most_common_count = max(bench_students_count.values(), default=0)
    
    # Return the most common count as the inferred students per bench
    return most_common_count



def create_roll_number_grid(room_data, students_per_bench=2):
    """
    Build the roll-number grid for a room.
    Students are placed sequentially column-by-column, 6 rows total.
    Example for 6 rows & 6 columns:
        1   7   13  19  25  31
        2   8   14  20  26  32
        3   9   15  21  27  33
        4   10  16  22  28  34
        5   11  17  23  29  35
        6   12  18  24  30  36
    """
    columns_per_row = 6 if students_per_bench == 2 else 9
    rows_per_room = 6  # fixed so 6×columns = capacity

    def extract_roll(obj):
        """Extract roll number string from Student_Id."""
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj.strip()
        if isinstance(obj, int):
            return str(obj)
        if hasattr(obj, 'RollNo'):
            return str(obj.RollNo).strip()
        return str(obj).strip()

    # 1. Extract roll numbers in the order from DB
    roll_numbers = [extract_roll(r.Student_Id) for r in room_data if r.Student_Id]

    # 2. Fill column-wise
    table_numbers = [[""] * columns_per_row for _ in range(rows_per_room)]
    idx = 0
    for col in range(columns_per_row):
        for row in range(rows_per_room):
            if idx < len(roll_numbers):
                table_numbers[row][col] = roll_numbers[idx]
                idx += 1

    # 3. Create table
    col_w = 72 if columns_per_row == 9 else 90
    table = Table(table_numbers, colWidths=[col_w] * columns_per_row, hAlign='CENTER')

    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))

    return table





def generate_attendance_sheet(request, room_no):
    normalized_room_no = room_no.strip()

    # Filter exactly like in your room-wise report: only CSE students
    allotments = ExamAllotment.objects.select_related('student').filter(
        room_no__iexact=normalized_room_no,
        student__department="Department of Computer Science and Engineering"
    ).order_by('student__roll_no')

    # PDF setup
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Attendance_Room_{room_no}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)

    p.setFont("Helvetica-Bold", 14)
    p.drawString(180, 800, f"Attendance Sheet - Room {normalized_room_no}")

    headers = ["S.No", "Roll No", "Name", "Signature"]
    x_positions = [50, 100, 250, 450]
    y = 770

    p.setFont("Helvetica-Bold", 12)
    for i, header in enumerate(headers):
        p.drawString(x_positions[i], y, header)

    y -= 25
    p.setFont("Helvetica", 11)

    if not allotments:
        p.drawString(200, y, "No students assigned to this room.")
    else:
        for i, allotment in enumerate(allotments, start=1):
            student = allotment.student
            if y < 100:
                p.showPage()
                p.setFont("Helvetica-Bold", 14)
                p.drawString(180, 800, f"Attendance Sheet - Room {normalized_room_no}")
                y = 770
                p.setFont("Helvetica-Bold", 12)
                for j, header in enumerate(headers):
                    p.drawString(x_positions[j], y, header)
                y -= 25
                p.setFont("Helvetica", 11)

            p.drawString(x_positions[0], y, str(i))
            p.drawString(x_positions[1], y, student.roll_no)
            p.drawString(x_positions[2], y, student.name)
            p.line(x_positions[3], y - 2, x_positions[3] + 100, y - 2)
            y -= 20

    p.save()
    return response
