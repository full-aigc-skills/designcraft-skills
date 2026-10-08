"""Conservative, offline structural probes for exported file formats."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'skills/designcraft-cli-export/scripts/format_probe.py'
SPEC=importlib.util.spec_from_file_location('format_probe',SCRIPT)
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class FormatProbeContract(unittest.TestCase):
    def test_pdf_reports_page_count_and_never_claims_visual_or_pdfx_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sample.pdf'
            path.write_bytes(b'%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n2 0 obj << /Type /Pages /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\n%%EOF\n')
            result=MODULE.probe(path,'pdf')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['pageCount'],1)
            self.assertFalse(result['completeAcceptance'])
            self.assertEqual(result['pdfxExternalCertification'],'NOT_RUN')
            self.assertEqual(result['visualContent'],'NOT_VERIFIED')

    def test_pdf_with_unparseable_structure_is_partial_and_bad_signature_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sample.pdf';path.write_bytes(b'%PDF-1.7\nopaque compressed objects\n%%EOF')
            self.assertEqual(MODULE.probe(path,'pdf')['status'],'PARTIAL')
            path.write_bytes(b'not pdf')
            self.assertEqual(MODULE.probe(path,'pdf')['status'],'FAIL')

    def test_png_dimensions_are_read_from_header_without_claiming_editability(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'image.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',640,480)+b'\x08\x02\x00\x00\x00'+b'\0'*4)
            result=MODULE.probe(path,'png')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual((result['width'],result['height']),(640,480))
            self.assertEqual(result['editability'],'NOT_APPLICABLE')

    def test_jpeg_webp_and_classic_tiff_report_dimensions(self):
        jpeg=b'\xff\xd8\xff\xc0\x00\x11\x08\x01\xe0\x02\x80\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00\xff\xd9'
        webp=b'RIFF'+(22).to_bytes(4,'little')+b'WEBPVP8X\x00\x00\x00\x00\x00\x00\x00\x00'+(639).to_bytes(3,'little')+(479).to_bytes(3,'little')
        tiff=b'II'+struct.pack('<HIH',42,8,2)+struct.pack('<HHI4s',256,4,1,struct.pack('<I',320))+struct.pack('<HHI4s',257,4,1,struct.pack('<I',240))+b'\x00'*4
        for name,data,expected in (('photo.jpg',jpeg,(640,480)),('image.webp',webp,(640,480)),('scan.tif',tiff,(320,240))):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/name;path.write_bytes(data)
                result=MODULE.probe(path)
                self.assertEqual(result['status'],'PASS',result)
                self.assertEqual((result['width'],result['height']),expected)

    def test_idml_checks_package_and_required_xml_but_not_target_app_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sample.idml'
            with zipfile.ZipFile(path,'w') as archive:
                archive.writestr('designmap.xml','<Document></Document>')
                archive.writestr('Stories/Story_u1.xml','<Story></Story>')
            result=MODULE.probe(path,'idml')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['targetAppReopen'],'NOT_RUN')
            self.assertEqual(result['editability'],'NOT_VERIFIED')

    def test_epub_checks_container_manifest_and_spine_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sample.epub'
            with zipfile.ZipFile(path,'w') as archive:
                archive.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
                archive.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="EPUB/package.opf"/></rootfiles></container>')
                archive.writestr('EPUB/package.opf','<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/></spine></package>')
                archive.writestr('EPUB/chapter.xhtml','<html/>')
            result=MODULE.probe(path,'epub')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['spineItemCount'],1)
            self.assertEqual(result['targetReaderReview'],'NOT_RUN')

    def test_zip_traversal_and_missing_spine_resource_fail_closed(self):
        for kind in ('idml','epub'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/f'sample.{kind}'
                with zipfile.ZipFile(path,'w') as archive:
                    archive.writestr('../escape.txt','bad')
                    if kind=='idml':archive.writestr('designmap.xml','<Document/>')
                    else:
                        archive.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
                        archive.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="p.opf"/></rootfiles></container>')
                        archive.writestr('p.opf','<package><manifest><item id="x" href="missing.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="x"/></spine></package>')
                self.assertEqual(MODULE.probe(path,kind)['status'],'FAIL')

if __name__=='__main__':unittest.main()
