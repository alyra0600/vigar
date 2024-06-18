# -*- coding: utf-8 -*-

import io
from base64 import urlsafe_b64decode
from logging import getLogger

from PIL import Image
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError

from odoo import _, models
from odoo.exceptions import UserError

logger = getLogger(__name__)


class PDFReport(models.Model):
    _inherit = "ir.actions.report"

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        result = super(PDFReport, self)._post_pdf(
            save_in_attachment, pdf_content=pdf_content, res_ids=res_ids
        )
        if not "professional_templates_invoice." in self.report_name:
            return result
        if result:
            report = self
            # watermark & last page uploaded at report level will override the
            # one uploaded at company level
            watermark = report.pdf_watermark or report.env.company.pdf_watermark or None
            last_page = report.pdf_last_page or report.env.company.pdf_last_page or None
            if watermark:
                try:
                    watermark = urlsafe_b64decode(watermark)
                except BaseException:
                    watermark = urlsafe_b64decode(watermark + b"===")
            if last_page:
                try:
                    last_page = urlsafe_b64decode(last_page)
                except BaseException:
                    last_page = urlsafe_b64decode(last_page + b"===")

            if not watermark and not last_page:
                return result
            pdf = PdfFileWriter()
            pdf_watermark = None
            if watermark:
                try:
                    pdf_watermark = PdfFileReader(io.BytesIO(watermark))
                    if pdf_watermark.isEncrypted:
                        try:
                            pdf_watermark.decrypt("")
                        except (NotImplementedError, Exception) as e:
                            pdf_watermark = None
                            msg = _(
                                "The uploaded watermark PDF document has security restrictions. Can not read or decrypt it!: "
                            )
                            msg += str(e)
                            logger.warning(msg)
                            raise UserError(msg)
                except PdfReadError:
                    try:
                        image = Image.open(io.BytesIO(watermark))
                        pdf_buffer = io.BytesIO()
                        if image.mode != "RGB":
                            image = image.convert("RGB")
                        resolution = image.info.get(
                            "dpi", report.paperformat_id.dpi or 90
                        )
                        if isinstance(resolution, tuple):
                            resolution = resolution[0]
                        # save the image as PDF
                        image.save(pdf_buffer, "pdf", resolution=resolution)
                        pdf_watermark = PdfFileReader(pdf_buffer)
                    except BaseException:
                        msg = _("Failed to load the non PDF watermark...")
                        logger.exception(msg)
                if not pdf_watermark:
                    msg = _("No usable watermark found, got ")
                    logger.info(msg + " %s", watermark[:100])

            if pdf_watermark and pdf_watermark.numPages < 1:
                msg = _(
                    "Your watermark pdf does not contain a page or is not a standard PDF document"
                )
                logger.info(msg)
                return result
            if pdf_watermark and pdf_watermark.numPages > 1:
                msg = _(
                    "Your watermark pdf contains more than one page. Only the first page will be used!"
                )
                logger.info(msg)
            doc = PdfFileReader(io.BytesIO(result))
            if pdf_watermark:
                for page in doc.pages:
                    watermark_page = pdf.addBlankPage(
                        page.mediaBox.getWidth(), page.mediaBox.getHeight()
                    )
                    # Use the first page of the watermark PDF only
                    watermark_page.mergePage(pdf_watermark.getPage(0))
                    watermark_page.mergePage(page)
            if last_page:
                pdf_last_page = PdfFileReader(io.BytesIO(last_page))
                if pdf_last_page.isEncrypted:
                    try:
                        pdf_last_page.decrypt("")
                    except (NotImplementedError, Exception) as e:
                        pdf_last_page = None
                        msg = _(
                            "The Last Page PDF document has security restrictions. Can not read or decrypt it!: "
                        )
                        msg += str(e)
                        logger.warning(msg)
                        raise UserError(msg)
                if not pdf_watermark:
                    for page in doc.pages:
                        pdf.addPage(page)
                if pdf_last_page:
                    for last in pdf_last_page.pages:
                        pdf.addPage(last)
            result = io.BytesIO()
            pdf.write(result)
            return result.getvalue()
        return result
