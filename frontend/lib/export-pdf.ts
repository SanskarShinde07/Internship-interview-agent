// Renders a DOM element to a downloadable multi-page PDF. jspdf and
// html2canvas-pro are dynamically imported so their ~200KB combined
// weight only loads when a candidate actually clicks "Download PDF", not
// on every report page visit.
//
// html2canvas-pro, not html2canvas: this design system uses Tailwind v4's
// opacity-modifier utilities (bg-accent/10, shadow-black/20, etc.), which
// Tailwind compiles to `color-mix(in oklab, ...)`. Plain html2canvas
// (last released before those color functions were common) throws
// "unsupported color function oklab" on them; the -pro fork parses
// oklab/oklch/color-mix correctly.

export async function exportElementToPdf(element: HTMLElement, filename: string): Promise<void> {
  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
    import("html2canvas-pro"),
    import("jspdf"),
  ]);

  const canvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: getComputedStyle(document.body).backgroundColor,
    useCORS: true,
  });

  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF({ orientation: "portrait", unit: "px", format: "a4" });

  const pdfWidth = pdf.internal.pageSize.getWidth();
  const pdfHeight = pdf.internal.pageSize.getHeight();
  const imgWidth = pdfWidth;
  const imgHeight = (canvas.height * imgWidth) / canvas.width;

  let heightRemaining = imgHeight;
  let position = 0;

  pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
  heightRemaining -= pdfHeight;

  while (heightRemaining > 0) {
    position = heightRemaining - imgHeight;
    pdf.addPage();
    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
    heightRemaining -= pdfHeight;
  }

  pdf.save(filename);
}
