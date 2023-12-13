from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import requests
from pipes import quote
from django.shortcuts import render
from django import forms
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.core.cache import cache
from bs4 import BeautifulSoup
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import ObjectItem 
from requests.adapters import Retry, HTTPAdapter
import re

#region Index
# Index
class IndexView(View):
    template_name = 'index.html'

    def get(self, request):
        data1 = self.fetch_data(request)  # Abrufen der Daten
        return render(request, self.template_name, {'data1': data1})
    
    def post(self, request):
        return self.fetch_data(request)
    
    def fetch_data(self,request):
        # URL, von der Daten abgerufen werden
        URL = 'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php#zvg_search'
        r = requests.get(URL)
        
        soup = BeautifulSoup(r.text, 'html.parser') # Parsen des HTML-Inhalts
        table = soup.find('table', {'id' : 'termineOutput'})

        data1 = []
        zvg_urls= fetch_url() # Abrufen der Objekt-URLs

        rows = table.find_all('tr')
        for index, row in enumerate(rows[1:], start=1):
            columns = row.find_all('td')

            if len(columns) >= 2:
                strong_tag = columns[0].find('strong')

                if strong_tag:
                    header = strong_tag.get_text()
                else:
                    header = ''

                obj_txt = ''
                br_tags = columns[0].find_all('br')

                if br_tags: 
                    for br_tag in br_tags:
                        obj_txt += br_tag.next_sibling.strip() + '\n'
   
                obj_date = columns[1].find('time')
                date = obj_date.get_text()

                link_tag = columns[0].find_all('a')[-1]  
                if link_tag:
                    obj_linktxt = link_tag.get_text(strip=True)

                if index <= len(zvg_urls):
                    url = zvg_urls[index - 1]
                    data1.append((header, obj_txt, obj_linktxt, date, url))
                else:
                    data1.append((header, obj_txt, obj_linktxt, date, None))
        return data1
    

# Objektdetails der Objekte auf der Startseite
class ObjectDetailsView(View):
    template_name = 'object_details.html'

    # Abruf Objektdetails von der angegebenen URL
    def fetch_object_details(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'anzeige'})

        if table:
            all_txt_content = [td.get_text(strip=True) for td in table.find_all('td')]
            first_row = table.find('tr')

            if first_row:
                aktenzeichen_tag = first_row.find('td')
                if aktenzeichen_tag:
                    aktenzeichen = aktenzeichen_tag.get_text(strip=True)

                aktualisierung_tag = first_row.find('td', {'align': 'right'})
                if aktualisierung_tag:
                    aktualisierung = aktualisierung_tag.get_text(strip=True)

                art_der_versteigerung = None
                grundbuch = None
                adresse = None
                objekttyp = None
                beschreibung = None
                verkehrswert = None
                termin = None
                ort_der_versteigerung = None

                for row in table.find_all('tr')[1:]:
                    columns = row.find_all('td')
                    if len(columns) == 2:
                        key = columns[0].get_text(strip=True)
            
                        if 'Objekt/Lage' in key:
                                objekt_lage_tag = row.find('b')
                                if objekt_lage_tag:
                                    objekttyp = objekt_lage_tag.get_text(strip=True).rstrip(':')  # Nachfolgenden Doppelpunkt entfernen
                                    if objekt_lage_tag.next_sibling:
                                        adresse = objekt_lage_tag.next_sibling.strip()
                
                index_of_art = all_txt_content.index('Art der Versteigerung:') +1 if 'Art der Versteigerung:' in all_txt_content else None
                art_der_versteigerung = all_txt_content[index_of_art] if index_of_art is not None else None

                index_of_gb = all_txt_content.index('Grundbuch:') + 1 if 'Grundbuch:' in all_txt_content else None
                grundbuch = all_txt_content[index_of_gb] if index_of_gb is not None else None

                index_of_vk = all_txt_content.index('Verkehrswert in €:') + 1 if 'Verkehrswert in €:' in all_txt_content else None
                verkehrswert = all_txt_content[index_of_vk] if index_of_vk is not None else None

                index_of_termin = all_txt_content.index('Termin:') + 1 if 'Termin:' in all_txt_content else None
                termin = all_txt_content[index_of_termin] if index_of_termin is not None else None

                index_of_ort = all_txt_content.index('Ort der Versteigerung:') + 1 if 'Ort der Versteigerung:' in all_txt_content else None
                ort_der_versteigerung = all_txt_content[index_of_ort] if index_of_ort is not None else None

                index_of_beschreibung = all_txt_content.index('Beschreibung:') + 1 if 'Beschreibung:' in all_txt_content else None
                beschreibung = all_txt_content[index_of_beschreibung] if index_of_beschreibung is not None else None
                
                details_dict = {
                    'Aktenzeichen' : aktenzeichen ,
                    'Aktualisierung' : aktualisierung,
                    'Art_der_Versteigerung' : art_der_versteigerung,
                    'Grundbuch' : grundbuch,
                    'Adresse' : adresse,
                    'Objekttyp': objekttyp,
                    'Beschreibung': beschreibung,
                    'Verkehrswert' : verkehrswert,
                    'Termin' : termin,
                    'Ort_der_Versteigerung' : ort_der_versteigerung,
                }

                return [details_dict]

    def generate_pdf(self, obj_data, file_name="objektdetails.pdf"):
        buffer = BytesIO()  # Puffer zum Speichern von PDF-Inhalten
        styles = getSampleStyleSheet()  # Stile für die PDF-Datei

        # PDF Dokument erstellen
        doc = SimpleDocTemplate(
            buffer,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            pagesize=letter
        )

        styles.add(ParagraphStyle(name='Blocksatz', parent=styles['Normal'], alignment=0))

        elements = []
        objekttyp = obj_data[0].get('Objekttyp', '')
        aktenzeichen = obj_data[0].get('Aktenzeichen', '')
        objektbeschreibung = obj_data[0].get('Beschreibung', '')
        art_der_versteigerung = obj_data[0].get('Art_der_Versteigerung')
        adresse_obj = obj_data[0].get('Adresse')
        grundbuch = obj_data[0].get('Grundbuch')
        verkehrswert = obj_data[0].get('Verkehrswert')
        termin_versteigerung = obj_data[0].get('Termin')

        aktualisierung = obj_data[0].get('Aktualisierung', '')

        header_text = f"<strong>{objekttyp}&nbsp; - &nbsp;{aktenzeichen}</strong>"
        elements.append(Paragraph(header_text, styles['Normal']))
        elements.append(Spacer(1, 12))  
        line_row = Table([[Spacer(1, 1)]], colWidths=[doc.width], rowHeights=[doc.height * 0.001])
        line_row.setStyle([('BACKGROUND', (0, 0), (-1, -1), colors.gray)])
        elements.append(line_row)

        elements.append(Spacer(1, 12)) 
        elements.append(Paragraph(f"<strong>Objektbeschreibung</strong>", styles['Normal'])) 
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"{objektbeschreibung}", styles['Normal']))
        elements.append(Spacer(1, 12))  

        line_row = Table([[Spacer(1, 1)]], colWidths=[doc.width], rowHeights=[doc.height * 0.001])
        line_row.setStyle([('BACKGROUND', (0, 0), (-1, -1), colors.gray)])
        elements.append(line_row) 

        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<strong>Objektinfos</strong>", styles['Normal']))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"Aktenzeichen: &nbsp;&nbsp; {aktenzeichen}", styles['Normal']))
        elements.append(Paragraph(f"Art der Versteigerung: &nbsp&nbsp{art_der_versteigerung}", styles['Normal']))
        elements.append(Paragraph(f"Objekttyp: &nbsp;&nbsp; {objekttyp}", styles['Normal']))  
        elements.append(Paragraph(f"Adresse: &nbsp;&nbsp; {adresse_obj}", styles['Normal'])) 
        elements.append(Paragraph(f"Grundbuch: &nbsp;&nbsp; {grundbuch}", styles['Normal'])) 
        elements.append(Paragraph(f"Verkehrswert: &nbsp;&nbsp; {verkehrswert}", styles['Normal'])) 
        elements.append(Paragraph(f"Termin der Versteigerung: &nbsp;&nbsp; {termin_versteigerung}", styles['Normal'])) 
        elements.append(Spacer(1, 12))

        line_row = Table([[Spacer(1, 1)]], colWidths=[doc.width], rowHeights=[doc.height * 0.001])
        line_row.setStyle([('BACKGROUND', (0, 0), (-1, -1), colors.gray)])
        elements.append(line_row)  

        styles.add(ParagraphStyle(name='RightAligned', alignment=2))
        elements.append(Paragraph(f"<small>{aktualisierung}</small>", styles['RightAligned']))

        # Erstellen des PDF-Dokuments
        doc.build(elements)

        buffer.seek(0) # Bewegen des Cursors an den Anfang des Puffers
        response = HttpResponse(buffer, content_type='application/pdf') # Erstellung einer HTTP-Antwort mit PDF-Inhalt
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'  # Einstellen des Dateinamens für den Download

        return response

    
    def get(self, request, url_index):
        url_data = fetch_url()

        if url_index < len(url_data):
            url = url_data[url_index] # Abrufen der URL auf der Grundlage des Index
            obj_data = self.fetch_object_details(url) # Objektdetails von der URL abrufen

            if obj_data:
                if request.GET.get('download_pdf') == '1':
                    form = forms.Form(request.GET)
                    form.fields['file_name'] = forms.CharField(max_length=255, required=True)

                    if form.is_valid():
                        file_name = form.cleaned_data['file_name']

                        if not file_name.endswith('.pdf'):
                            file_name += '.pdf'

                        file_name_encoded = quote(file_name)
                        pdf_response = self.generate_pdf(obj_data, file_name)
                        pdf_response['Content-Disposition'] = f'attachment; filename="{file_name_encoded}"'
                        return pdf_response
                    else:
                        return HttpResponse("Ungültige Eingabe im Formular")
                else:
                    return render(request, self.template_name, {'obj_data': obj_data})
            else:
                return HttpResponse("Objekt nicht gefunden")
        else:
            return HttpResponse("Ungültiger Index")


# URLs von den Objekten der Startseite abrufen
def fetch_url():
    URL = 'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php#zvg_search'
    r = requests.get(URL)

    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table')
    zvg_urls = []

    rows = table.find_all('tr')

    for row in rows[1:]: 
        columns = row.find_all('td')

        if len(columns) >= 2:
            links = columns[0].find_all('strong')
            url_link = links[0].find_all('a')

            for link in url_link:
                href = link.get('href') 
                
                if href:
                    zvg_url = href 
                    zvg_urls.append((zvg_url)) 

    return zvg_urls 
#endregion


#region Ortsauswahl
# Auswahl Stadt
class SelectedCityView(View):
    template_name = 'city_selection.html'
    
    def get(self, request):
        city_data = fetch_and_process_city_data()
        city_radius = fetch_and_process_radius_data()
        radius_data = [{'value': key, 'text': value['Text']} for key, value in city_radius.items()]

        context = {
            'city_data': city_data,
            'radius_data': radius_data,
        }

        return render(request, self.template_name, context)
    

# View Auswahl Stadt
class ObjectView(View):
    template_name = 'object_data.html'

    def get(self, request):
        selected_city = request.GET.get('city')
        data = self.fetch_data(selected_city)
        return render(request, self.template_name, {'data': data})

    def post(self, request):
        selected_city = request.POST.get('city')
        return self.fetch_data(selected_city)

    def fetch_data(self, selected_city):
        city_data = fetch_and_process_city_data().get(selected_city)
        zvg_id = city_data.get('zvgID')

        URL = f'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php?zvgId={zvg_id}&x=21&y=12&zvgZIPorCity=&zvgRadius=0&formIsSent=1#zvg_search'

        response = requests.get(URL)

        if response.status_code != 200:
            return []

        return self.process_html(response.text, selected_city)

    def process_html(self, html_text, selected_city):
        soup = BeautifulSoup(html_text, 'html.parser')
        table = soup.find('table', id='termineOutput')

        data = []

        rows = table.find_all('tr')
        for index, row in enumerate(rows[1:], start=1):
            columns = row.find_all('td')

            if len(columns) >= 2:
                strong_tag = columns[0].find('strong')
                info_header = strong_tag.get_text() if strong_tag else ''
                
                obj_text = ""
                br_tags = columns[0].find_all('br')

                for br_tag in br_tags:
                    next_sibling = br_tag.next_sibling
                    if next_sibling and isinstance(next_sibling, str): 
                        obj_text += next_sibling.strip() + '\n'

                date = columns[1].find('time').get_text() if columns[1].find('time') else ''

                city_url_data = fetch_city_url(selected_city)
                city_url = city_url_data[index - 1] if index <= len(city_url_data) else None

                data.append((info_header, obj_text, date, city_url))

        return data


#View Radius und ausgewählter Umkreis
class ObjectDataRadiusView(View):
    template_name = 'object_data_radius.html'

    def get(self, request):
        selected_radius = request.GET.get('zvgR')
        zip_or_city = request.GET.get('zvgZIPorCity')
        data_radius = self.fetch_data(selected_radius, zip_or_city)
        return render(request, self.template_name, {'data_radius': data_radius})

    def post(self, request):
        selected_radius = request.POST.get('zvgR')
        zip_or_city = request.POST.get('zvgZIPorCity')
        return self.fetch_data(selected_radius, zip_or_city)
    
    def fetch_data(self, selected_radius, zip_or_city):
        print("zip_or_city:", zip_or_city)
        radius_data = fetch_and_process_radius_data().get(selected_radius)
        zvgRadius = radius_data.get('zvgR')
        URL = f'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php?zvgId=&zvgZIPorCity={zip_or_city}&zvgRadius={zvgRadius}&x=24&y=14&formIsSent=1#zvg_search'
        print(URL)
        response = requests.get(URL)
        
        if response.status_code != 200:
            return []
        
        return self.process_html(response.text, selected_radius, zip_or_city)
    
    def process_html(self, html_content, selected_radius, zip_or_city):
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', id='termineOutput')

        data1 = []

        rows = table.find_all('tr')
        for index, row in enumerate(rows[1:], start=1):
            columns = row.find_all('td')

            if len(columns) >= 2:
                strong_tag = columns[0].find('strong')
                info_header = strong_tag.get_text() if strong_tag else ''

                obj_txt = ""
                br_tags = columns[0].find_all('br')

                for br_tag in br_tags:
                    next_sibling = br_tag.next_sibling
                    if next_sibling and isinstance(next_sibling, str): 
                        obj_txt += next_sibling.strip() + '\n'

                date = columns[1].find('time').get_text() if columns[1].find('time') else ''

                city_url_data = fetch_radius_url(selected_radius, zip_or_city)
                city_url = city_url_data[index - 1] if index <= len(city_url_data) else None

                data1.append((info_header, obj_txt, date, city_url))
                
        return data1


# Ansicht der Objektdetails, Auswahl Stadt
class ObjectCityDetailView(View):
    template_name = 'object_city_details.html'

    def fetch_object_details(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'anzeige'})

        if table:
            all_txt = [td.get_text(strip=True) for td in table.find_all('td')]
            first_row = table.find('tr')
            if first_row:
                aktenzeichen_tag = first_row.find('td')
                if aktenzeichen_tag:
                    aktenzeichen = aktenzeichen_tag.get_text(strip=True)

                aktualisierung_tag = first_row.find('td', {'align': 'right'})
                if aktualisierung_tag:
                    aktualisierung = aktualisierung_tag.get_text(strip=True)

                art_der_versteigerung = None
                grundbuch = None
                adresse = None
                objekttyp = None
                beschreibung = None
                verkehrswert = None
                termin = None
                ort_der_versteigerung = None

                for row in table.find_all('tr')[1:]:
                    columns = row.find_all('td')
                    if len(columns) == 2:
                        key = columns[0].get_text(strip=True)

                        if 'Objekt/Lage' in key:
                            objekt_lage_tag = row.find('b')
                            if objekt_lage_tag:
                                objekttyp = objekt_lage_tag.get_text(strip=True).rstrip(':')  
                                if objekt_lage_tag.next_sibling:
                                    adresse = objekt_lage_tag.next_sibling.strip()
                
                index_art = all_txt.index('Art der Versteigerung:') + 1 if 'Art der Versteigerung:' in all_txt else None
                art_der_versteigerung = all_txt[index_art] if index_art is not None else None

                index_gb = all_txt.index('Grundbuch:') + 1 if 'Grundbuch:' in all_txt else None
                grundbuch = all_txt[index_gb] if index_gb is not None else None

                index_b = all_txt.index('Beschreibung:') + 1 if 'Beschreibung:' in all_txt else None
                beschreibung = all_txt[index_b] if index_b is not None else None

                index_v = all_txt.index('Verkehrswert in €:') + 1 if 'Verkehrswert in €:' in all_txt else None
                verkehrswert = all_txt[index_v] if index_v is not None else None

                index_t = all_txt.index('Termin:') + 1 if 'Termin:' in all_txt else None
                termin = all_txt[index_t] if index_t is not None else None

                index_o = all_txt.index('Ort der Versteigerung:') + 1 if 'Ort der Versteigerung:' in all_txt else None
                ort_der_versteigerung = all_txt[index_o] if index_o is not None else None

                city_details_dict = {
                    'Aktenzeichen' : aktenzeichen ,
                    'Aktualisierung' : aktualisierung,
                    'Art_der_Versteigerung' : art_der_versteigerung,
                    'Grundbuch' : grundbuch,
                    'Adresse' : adresse,
                    'Objekttyp': objekttyp,
                    'Beschreibung': beschreibung,
                    'Verkehrswert' : verkehrswert,
                    'Termin' : termin,
                    'Ort_der_Versteigerung' : ort_der_versteigerung,
                }

                return [city_details_dict]

    def generate_pdf(self, object_data, file_name='object_details.pdf'):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        elements.append(Paragraph(object_data['header'], styles['Title']))

        details = []

        for detail in object_data['object_data']:
            details.append([Paragraph(detail['info'], styles['Normal']), Paragraph(detail['detail'], styles['Normal'])])

        table_style = TableStyle(
            [('BACKGROUND', (0, 0), (-1, 0), colors.gray),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)]
        )

        details_table = Table(details)
        details_table.setStyle(table_style)
        elements.append(details_table)
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'

        return response

    def get(self, request, selected_city, city_url_index):
        city_url_data = fetch_city_url(selected_city)

        if city_url_index < len(city_url_data):
            city_url = city_url_data[city_url_index]
            object_data = self.fetch_object_details(city_url)

            if object_data:
        
                if request.GET.get('download_pdf') == '1':
                    file_name = request.GET.get('file_name', 'object_city_details')
        
                    if not file_name.endswith('.pdf'):
                        file_name += '.pdf'
        
                    file_name_encoded = quote(file_name)    
                    pdf_response = self.generate_pdf(object_data)
                    pdf_response['Content-Disposition'] = f'attachment; filename="{file_name_encoded}"'
                    return pdf_response
                else:
                    return render(request, self.template_name, {'object_data': object_data})
            else:
                return HttpResponse("Objekt nicht gefunden")
        else:
            return HttpResponse("Ungültiger Index")


# View Objektdetails, Radius und Auswahl Umkreis
class ObjectRadiusDetailView(View):
    template_name = 'object_radius_details.html'

    def fetch_object_details(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'anzeige'})

        first_row = table.find('tr')
        if first_row:
            aktenzeichen_tag = first_row.find('td')
            if aktenzeichen_tag:
                aktenzeichen = aktenzeichen_tag.get_text(strip=True)

            aktualisierung_tag = first_row.find('td', {'align': 'right'})
            if aktualisierung_tag:
                aktualisierung = aktualisierung_tag.get_text(strip=True)

        art_der_versteigerung = None
        grundbuch = None
        adresse = None
        objekttyp = None
        beschreibung = None
        verkehrswert = None
        termin = None
        ort_der_versteigerung = None

        for row in table.find_all('tr')[1:]:
            columns = row.find_all('td')
            if len(columns) == 2:
                key = columns[0].get_text(strip=True)
                value = columns[1].get_text(strip=True)

                if 'Art der Versteigerung' in key:
                    art_der_versteigerung = value
                elif 'Grundbuch' in key:
                    grundbuch = value
                elif 'Objekt/Lage' in key:
                    objekt_lage_tag = row.find('b')
                    if objekt_lage_tag:
                        objekttyp = objekt_lage_tag.get_text(strip=True).rstrip(':')  
                        if objekt_lage_tag.next_sibling:
                            adresse = objekt_lage_tag.next_sibling.strip()
                elif 'Beschreibung' in key:
                    beschreibung = value
                elif 'Verkehrswert' in key:
                    verkehrswert = value
                elif 'Termin' in key:
                    termin = value
                elif 'Ort der Versteigerung' in key:
                    ort_der_versteigerung = value

        details_radius_dict = {
            'Aktenzeichen' : aktenzeichen ,
            'Aktualisierung' : aktualisierung,
            'Art_der_Versteigerung' : art_der_versteigerung,
            'Grundbuch' : grundbuch,
            'Adresse' : adresse,
            'Objekttyp': objekttyp,
            'Beschreibung': beschreibung,
            'Verkehrswert' : verkehrswert,
            'Termin' : termin,
            'Ort_der_Versteigerung' : ort_der_versteigerung,
        }
        return [details_radius_dict]

    def generate_pdf(self, object_data, file_name='object_details.pdf'):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        elements.append(Paragraph(object_data['header'], styles['Title']))

        details = []

        for detail in object_data['object_data']:
            details.append([Paragraph(detail['info'], styles['Normal']), Paragraph(detail['detail'], styles['Normal'])])

        table_style = TableStyle(
            [('BACKGROUND', (0, 0), (-1, 0), colors.gray),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)]
        )

        details_table = Table(details)
        details_table.setStyle(table_style)
        elements.append(details_table)
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'

        return response

    def get(self, request, selected_radius, zip_or_city, city_url_index):
        city_url_data = fetch_radius_url(selected_radius, zip_or_city)

        if city_url_index < len(city_url_data):
            city_url = city_url_data[city_url_index]
            object_data = self.fetch_object_details(city_url)

            if object_data:
        
                if request.GET.get('download_pdf') == '1':
                    file_name = request.GET.get('file_name', 'object_city_details')
        
                    if not file_name.endswith('.pdf'):
                        file_name += '.pdf'
        
                    file_name_encoded = quote(file_name)    
                    pdf_response = self.generate_pdf(object_data)
                    pdf_response['Content-Disposition'] = f'attachment; filename="{file_name_encoded}"'
                    return pdf_response
                else:
                    return render(request, self.template_name, {'object_data': object_data})
            else:
                return HttpResponse("Objekt nicht gefunden")
        else:
            return HttpResponse("Ungültiger Index")

def fetch_and_process_city_data():
    URL = 'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php#zvg_search'
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    select = soup.find('select', id='zvgId')
    zvgIDs = []

    if select:
        options = select.find_all('option')

        for index, option in enumerate(options):
            if index >= 1:
                zvgID = option.get('value')
                zvgTXT = option.get_text()
                zvgIDs.append((zvgID, zvgTXT))

    city_data = {}
    for zvgID, zvgTXT in zvgIDs:
        city_data[zvgTXT] = {
            'zvgID': zvgID,
            'header': f'Übersicht über bis zu 10 aktuelle Versteigerungstermine des Amtsgerichts {zvgTXT}'
        }
    return city_data

def fetch_and_process_radius_data():
    URL = 'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php#zvg_search'
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    select = soup.find('select', id='zvgRadius')
    zvgRadius = []

    if select:
        options = select.find_all('option')

        for Radius_index, option in enumerate(options):
            if Radius_index >= 0:
                zvgR = option.get('value')
                zvgRtxt = option.get_text()
                zvgRadius.append((zvgR, zvgRtxt))

    radius_data = {}
    for zvgR, zvgRtxt in zvgRadius:
        radius_data[zvgR] = {
            'zvgR': zvgR,
            'Text': zvgRtxt
        }

    return radius_data

# URLs der Objekte, Auswahl Stadt
def fetch_city_url(selected_city):
    cached_urls = cache.get(f'zvg_urls_{selected_city}')
    if cached_urls:
        return cached_urls

    urls = _fetch_city_url_without_cache(selected_city)
    cache.set(f'zvg_urls_{selected_city}', urls, 60 * 15)
    return urls

def _fetch_city_url_without_cache(selected_city):
    dict_city = fetch_and_process_city_data() 
    
    if selected_city in dict_city:
        city_datas = dict_city[selected_city] 
        zvgID = city_datas['zvgID'] 
        URL = f'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php?zvgId={zvgID}&x=18&y=6&zvgZIPorCity=&zvgRadius=0&formIsSent=1#zvg_search'
        r = requests.get(URL)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table')

        if table:
            zvg_urls = [] 
            rows = table.find_all('tr')[1:] 
            
            for row in rows:
                columns = row.find_all('td')
                if len(columns) >= 2:
           
                    links = columns[0].find_all('strong')[0].find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href:
                            zvg_urls.append(href)
            return zvg_urls 
        else:
            return [] 
    else:
        return [] 

def fetch_radius_url(selected_radius, zip_or_city):
    cached_urls = cache.get(f'zvgR_urls_{selected_radius}')

    if cached_urls is not None:
        return cached_urls

    # Fetch the URLs from the external URL
    urls = _fetch_radius_url_without_cache(selected_radius, zip_or_city)

    # Store the URLs in the cache for 15 minutes (60 * 15 seconds)
    cache.set(f'zvgR_urls_{selected_radius}', urls, 60 * 15)

    return urls

def _fetch_radius_url_without_cache(selected_radius, zip_or_city):
    dict_radius = fetch_and_process_radius_data()

    if selected_radius in dict_radius:
        radius_datas = dict_radius[selected_radius]
        zvgR = radius_datas['zvgR']
        URL = f'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php?zvgId=&zvgZIPorCity={zip_or_city}&zvgRadius={zvgR}&x=24&y=14&formIsSent=1#zvg_search'
        r = requests.get(URL)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table')

        if table:
            zvgR_urls = [] # Initialize a list to store the URLs
            rows = table.find_all('tr')[1:] # Skip the header row
            
            for row in rows:
                columns = row.find_all('td')
                if len(columns) >= 2:
                    # Find and collect the URLs from the table
                    links = columns[0].find_all('strong')[0].find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href:
                            zvgR_urls.append(href)
            return zvgR_urls # Return the list of URLs
        else:
            return [] # Return an empty list if the table isn't found
    else:
        return [] # Return an empty list
#endregion


#region Objektsuche
# Objektsuche /Ort/Typ
class DetailSearch(View):
    template_name = 'detail_search.html'

    def get(self, request):
        object_data = self.fetch_datas(request)
        bundesland_data = self.fetch_data(request)
        stadt_data = fetch_staedte()

        bdl_data = []
        for key, value in bundesland_data.items():
            stadt_list = stadt_data.get(key, {}).get('text', [])
            bdl_data.append({'value': key, 'text': value['bundesland_txt'], 'staedte': stadt_list})
        return render(request, self.template_name, {'bdl_data': bdl_data, 'object_data': object_data })

    def post(self, request):
        object_data = self.fetch_datas(request)
        bundesland_data = self.fetch_data(request)
        stadt_data = fetch_staedte()

        bdl_data = []
        for key, value in bundesland_data.items():
            stadt_list = stadt_data.get(key, {}).get('text', [])
            bdl_data.append({'value': key, 'text': value['bundesland_txt'], 'staedte': stadt_list})

        return render(request, self.template_name, {'bdl_data': bdl_data, 'object_data': object_data })

    def fetch_data(self, request):
            URL = 'https://www.zvg-portal.de/index.php?button=Termine%20suchen'
            response = requests.get(URL)
            soup = BeautifulSoup(response.text, 'html.parser')

            bundesland_data = {}   
            s_bundesland = soup.find('select', {'name': 'land_abk'})
            if s_bundesland:
                bundeslaender = s_bundesland.find_all('option')
                
                for option in bundeslaender:
                    bundesland_value = option['value']
                    bundesland_txt = option.get_text().strip()
                    bundesland_data[bundesland_value] = {
                        'bundesland_txt': bundesland_txt,
                        'bundesland_value': bundesland_value
                    }

            return bundesland_data
    
    def fetch_datas(self, request):
        URL = 'https://www.zvg-portal.de/index.php?button=Termine%20suchen'
        response = requests.get(URL)
        soup = BeautifulSoup(response.text, 'html.parser')


        obj_art = []   
        s_obj_art = soup.find('select', {'name': 'obj_liste'})
        if s_obj_art:
            obj_arts = s_obj_art.find_all('option')
            obj_art = [{'text': option.text.strip(), 'value': option.get('value', None)} for option in obj_arts]
        return obj_art
    
#extrahieren des Arrays BundeslandArrayId vom script
def fetch_staedte_ID():
    URL = 'https://www.zvg-portal.de/index.php?button=Termine%20suchen'
    response = requests.get(URL)
    html_content = response.text

    bl_staedte_ID = re.compile(r"BundeslandArrayId\['(\w+)'\]=new Array\((.*?)\);", re.DOTALL)
    matches_bl_ID = bl_staedte_ID.findall(html_content)
    bundesland_staedteID_data = {}

    for match in matches_bl_ID:
        key = match[0]
        id = [id.strip("'") for id in match[1].split(',')]

        bundesland_staedteID_data[key] = {
            'value': key,
            'text': id
        }

    return bundesland_staedteID_data

#extrahieren des Arrays BundeslandArray vom script
def fetch_staedte():
    URL = 'https://www.zvg-portal.de/index.php?button=Termine%20suchen'
    response = requests.get(URL)
    html_content = response.text

    bl_staedte = re.compile(r"BundeslandArray\['(\w+)'\]=new Array\((.*?)\);", re.DOTALL)
    matches_bl_staedte = bl_staedte.findall(html_content)
    bundesland_staedte_data = {}

    bID = fetch_staedte_ID()

    for match in matches_bl_staedte:
        key = match[0]
        stadt_ids = [id.strip("'") for id in bID.get(key, {}).get('text', [])]
        stadt_names = [stadt.strip("'") for stadt in match[1].split(',')]
        bundesland_staedte_data[key] = {
            'value': key,
            'text': [{'id': id, 'name': name} for id, name in zip(stadt_ids, stadt_names)]
        }

    return bundesland_staedte_data
    
#Liste der Termine Objektsuche
class TerminObjektlisteView(View):
    template_name = 'objekt_liste.html'
    external_url = 'https://www.zvg-portal.de/index.php?button=Suchen&all=1'
                  
    def post(self, request):
        form_data = self.extract_form_data(request)
        response = requests.post(self.external_url, data=form_data)
        extracted_data = self.extract_data(response.text)
        
        return render(request, self.template_name, {'extracted_data': extracted_data})

    def extract_form_data(self, request):
        ger_name = request.POST.get('ger_name')
        land_abk = request.POST.get('land_abk')
        ger_id = request.POST.get('ger_id')
        obj = request.POST.get('obj')
        obj_arr = request.POST.getlist('obj_arr[]')

        last_added_element_obj_liste = obj_arr[-1] if obj_arr else None

        form_data = {
            'ger_name': ger_name,
            'order_by': '2',
            'land_abk': land_abk,
            'ger_id': ger_id,
            'az1': '',
            'az2': '',
            'az3': '',
            'az4': '',
            'art': '',
            'obj': obj,
            'obj_arr[]': obj_arr,
            'obj_liste': last_added_element_obj_liste,
            'str': '',
            'hnr': '',
            'plz': '',
            'ort': '',
            'ortsteil': '',
            'vtermin': '',
            'btermin': ''
        }

        return form_data

    def extract_data(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        tr_tags = soup.find_all('tr')
        extracted_data = []

        objekttyp_value = None
        adresse = None
        amtsgericht_value = None
        termin_value = None
        link_value = None

        for tr_tag in tr_tags:
            td_tags = tr_tag.find_all('td')
            
            if td_tags and 'Aktenzeichen' in td_tags[0].get_text():
                link_tag = td_tags[1].find('a')
                if link_tag:
                    url = f'https://www.zvg-portal.de/'
                    link = link_tag['href']
                    session_ID = '&sessionId=VNP21qQE09'
                    link_value = url + link + session_ID
                    
            if td_tags and 'Objekt/Lage' in td_tags[0].get_text():
                objekttyp_value = td_tags[1].find('b').get_text(strip=True).rstrip(':')

            if td_tags and 'Objekt/Lage' in td_tags[0].get_text():
                adresse_tag = td_tags[1]
                if adresse_tag:
                    adresse_value = adresse_tag.get_text(strip=True)
                    adresse_parts = adresse_value.split('</b>')
                    adresse = [part.split(':')[-1].strip() for part in adresse_parts]

            if td_tags and 'Amtsgericht' in td_tags[0].get_text():
                amtsgericht_tag = td_tags[1].find('b')
                if amtsgericht_tag:
                    amtsgericht_value = amtsgericht_tag.get_text(strip=True).replace('in ', '')

            if td_tags and 'Termin' in td_tags[0].get_text():
                termin_value = td_tags[1].get_text(strip=True)

            if objekttyp_value is not None and amtsgericht_value is not None and adresse is not None and termin_value is not None and link_value is not None:
                extracted_data.append({
                    'Link': link_value,
                    'Objekttyp': objekttyp_value,
                    'Adresse': adresse,
                    'Amtsgericht': amtsgericht_value,
                    'Termin': termin_value
                })
                link_value = None
                objekttyp_value = None
                adresse = None
                amtsgericht_value = None
                termin_value = None

        return extracted_data
                        

#Objektdetails der Deteilsuche/Terminliste
class ObjektdetailsSucheView(View):
    temaplate_name = 'objektdetails.html'

    def get(self, request):
        selected_link = request.get_full_path().split('selected_link=')[1]
        object_details = self.fetch_data(selected_link)

        return render(request, self.temaplate_name, {'object_details': object_details})

    def fetch_data(self, selected_link):
        response = requests.get(selected_link)        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'anzeige'})

        if table:
            all_td_text_content = [td.get_text(strip=True) for td in table.find_all('td')]
            first_row = table.find('tr')
            if first_row:
                aktenzeichen_tag = first_row.find('td')
                if aktenzeichen_tag:
                    aktenzeichen = aktenzeichen_tag.get_text(strip=True)

                aktualisierung_tag = first_row.find('td', {'align': 'right'})
                if aktualisierung_tag:
                    aktualisierung = aktualisierung_tag.get_text(strip=True)

                art_der_versteigerung = None
                grundbuch = None
                adresse = None
                objekttyp = None
                beschreibung = None
                verkehrswert = None
                termin = None
                ort_der_versteigerung = None

                for row in table.find_all('tr')[1:]:
                    columns = row.find_all('td')
                    if len(columns) == 2:
                        key = columns[0].get_text()
                    
                        if 'Objekt/Lage' in key:
                            objekt_lage_tag = row.find('b')
                            if objekt_lage_tag:
                                objekttyp = objekt_lage_tag.get_text(strip=True).rstrip(':') 
                                if objekt_lage_tag.next_sibling:
                                    adresse = objekt_lage_tag.next_sibling.strip()
                        
                index_of_art = all_td_text_content.index('Art der Versteigerung:') + 1 if 'Art der Versteigerung:' in all_td_text_content else None
                art_der_versteigerung = all_td_text_content[index_of_art] if index_of_art is not None else None

                index_of_gb = all_td_text_content.index('Grundbuch:') + 1 if 'Grundbuch:' in all_td_text_content else None
                grundbuch = all_td_text_content[index_of_gb] if index_of_gb is not None else None

                index_of_vk = all_td_text_content.index('Verkehrswert in €:') + 1 if 'Verkehrswert in €:' in all_td_text_content else None
                verkehrswert = all_td_text_content[index_of_vk] if index_of_vk is not None else None

                index_of_termin = all_td_text_content.index('Termin:') + 1 if 'Termin:' in all_td_text_content else None
                termin = all_td_text_content[index_of_termin] if index_of_termin is not None else None

                index_of_ort = all_td_text_content.index('Ort der Versteigerung:') + 1 if 'Ort der Versteigerung:' in all_td_text_content else None
                ort_der_versteigerung = all_td_text_content[index_of_ort] if index_of_ort is not None else None

                index_of_beschreibung = all_td_text_content.index('Beschreibung:') + 1 if 'Beschreibung:' in all_td_text_content else None
                beschreibung = all_td_text_content[index_of_beschreibung] if index_of_beschreibung is not None else None


                details_dict = {
                    'Aktenzeichen' : aktenzeichen ,
                    'Aktualisierung' : aktualisierung,
                    'Art_der_Versteigerung' : art_der_versteigerung,
                    'Grundbuch' : grundbuch,
                    'Adresse' : adresse,
                    'Objekttyp': objekttyp,
                    'Beschreibung': beschreibung,
                    'Verkehrswert' : verkehrswert,
                    'Termin' : termin,
                    'Ort_der_Versteigerung' : ort_der_versteigerung,
                }

                return [details_dict]
#endregion


#region alle Objekte
class ObjectItem:
    
    def __init__(self, info_header, obj_text, date, url):
        self.info_header = info_header
        self.obj_text = obj_text
        self.date = date
        self.url = url


# Alle Objekte
class AllObjectsView(View):
    template_name = 'all_objects_details.html'
    items_per_page = 10

    def get(self, request):
        all_objects = cache.get('all_objects_cached_data')

        if not all_objects:
            all_objects = self.fetch_and_process_data()
            cache.set('all_objects_cached_data', all_objects, 60 * 15) 

        paginator = Paginator(all_objects, self.items_per_page)
        page = request.GET.get('page')

        try:
            all_objects = paginator.page(page)
        except PageNotAnInteger:
            all_objects = paginator.page(1)
        except EmptyPage:
            all_objects = paginator.page(paginator.num_pages)

        return render(request, self.template_name, {'all_objects': all_objects})
    
    def fetch_and_process_data(self):
        dict_city = fetch_and_process_city_data()
        all_objects = []

        for city, city_data in dict_city.items():
            city_datas = city_data
            zvgID = city_datas['zvgID']
            header = city_datas['header']
            URL = f'https://www.justiz.nrw.de/JM/doorpage_online_verfahren_projekte/projekte_fuer_den_buerger/zvg_auskunft/index.php?zvgId={zvgID}&x=21&y=12&zvgZIPorCity=&zvgRadius=0&formIsSent=1#zvg_search'
            data = []

            response = requests.get(URL)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', id='termineOutput')
                zvg_urls = fetch_url()
                rows = table.find_all('tr')

                for index, row in enumerate(rows[1:], start=1):
                    columns = row.find_all('td')

                    if len(columns) >= 2:
                        strong_tag = columns[0].find('strong')

                        if strong_tag:
                            header = strong_tag.get_text()
                        else:
                            header = ''

                        obj_text = ''
                        br_tags = columns[0].find_all('br')
                        for br_tag in br_tags:
                            if br_tag.next_sibling:
                                obj_text += br_tag.next_sibling.strip() + '\n'

                        get_date = columns[1].find('time')
                        date = get_date.get_text()

                        if index <= len(zvg_urls):
                            url = zvg_urls[index - 1]
                            obj = ObjectItem(header, obj_text, date, url)
                            data.append(obj)
                        else:
                            obj = ObjectItem(header, obj_text, date, None)
                            data.append(obj)

                all_objects.extend(data)

        return all_objects
#endregion


#region Amtsgerichte
#Auswahl Bundesland für Liste Amtsgerichte
class AmtsgerichteView(View):
    template_name = 'amtsgerichte.html'

    def get(self, request):
        amtg = self.fetch_and_process_bdl_data()
        return render(request, self.template_name, {'amtg': amtg})

    def fetch_and_process_bdl_data(self):  
        URL = 'https://gerichte-und-staatsanwaltschaften.de/amtsgerichte/'
        response = requests.get(URL)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        amtgerichte_ul_list = soup.select('div.nv-content-wrap.entry-content ul')

        text_list = []

        if len(amtgerichte_ul_list) >= 4:
            drittes_ul = amtgerichte_ul_list[4]
            bdl_txt = drittes_ul.find_all('a')
            if bdl_txt:
                for a_element in bdl_txt:
                    text = a_element.get_text()
                    text_list.append(text)
        return text_list

"""
class AmtsgerichteStaedte(View):
    template_name = 'bdl_city.html'
"""


#endregion        

"""TODO:
Änderungen an den Objektdetails für Auswahl Stadt/Radius
- Methoden zusammenfassen
- Liste Amtsgerichte hinzufügen
"""
