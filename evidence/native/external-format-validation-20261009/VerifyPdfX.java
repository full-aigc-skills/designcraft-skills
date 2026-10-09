import com.qoppa.pdfPreflight.PDFPreflight;
import com.qoppa.pdfPreflight.profiles.PDFX_4_Profile;
import com.qoppa.pdfPreflight.results.PreflightResults;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
/** 使用独立 Qoppa 引擎检查指定 PDF，不转换或写回输入。 */
public final class VerifyPdfX {
    public static void main(String[] args) throws Exception {
        PDFPreflight document = new PDFPreflight(args[0], null);
        try {
            PDFX_4_Profile profile = new PDFX_4_Profile();
            PreflightResults result = document.verifyDocument(profile, null);
            try (PrintStream output = new PrintStream(args[1], StandardCharsets.UTF_8)) {
                output.println("engine=" + PDFPreflight.getVersion());
                output.println("profile=" + profile.getName());
                output.println("profileVersion=" + profile.getVersionIdentifier());
                output.println("pages=" + document.getPageCount());
                output.println("compliant=" + result.isSuccessful());
                output.println("resultRecords=" + result.getResults().size());
                result.echoResults(output);
            }
            result.savePreflightReport(Path.of(args[1] + ".pdf").toString(), 612, 792);
            System.out.println("profile=" + profile.getName() + " compliant=" + result.isSuccessful());
        } finally {
            document.close();
        }
    }
}
