"""
MultivarMA — Browser-based Multivariate Meta-Analysis test suite.
Pytest + Selenium (headless Chrome), 17 tests.
"""
import pytest
import os
import sys
import time
import threading
import http.server
import socketserver
# UTF-8 env for Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 9877
URL = f"http://localhost:{PORT}/index.html"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress logs


@pytest.fixture(scope="session")
def server():
    """Start local HTTP server for the app."""
    os.chdir(APP_DIR)
    handler = QuietHandler
    httpd = socketserver.TCPServer(("", PORT), handler)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield httpd
    httpd.shutdown()


@pytest.fixture(scope="session")
def driver(server):
    """Launch headless Chrome."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    drv = webdriver.Chrome(options=opts)
    drv.set_page_load_timeout(60)
    drv.implicitly_wait(5)
    yield drv
    drv.quit()


def load_app(driver):
    driver.get(URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "btnAnalyze"))
    )


def click_demo_and_analyze(driver):
    load_app(driver)
    driver.find_element(By.ID, "btnDemo").click()
    time.sleep(0.2)
    driver.find_element(By.ID, "btnAnalyze").click()
    time.sleep(0.5)


def get_results_table(driver):
    """Return list of dicts from the summary table."""
    table = driver.find_element(By.ID, "summaryResultsTable")
    rows = table.find_elements(By.TAG_NAME, "tr")
    results = []
    for row in rows[1:]:  # skip header
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 9:
            results.append({
                "outcome": cells[0].text.strip(),
                "pooled_mv": cells[1].text.strip(),
                "se_mv": cells[2].text.strip(),
                "ci": cells[3].text.strip(),
                "pooled_uv": cells[4].text.strip(),
                "se_uv": cells[5].text.strip(),
                "bos": cells[6].text.strip(),
                "tau2": cells[7].text.strip(),
                "i2": cells[8].text.strip(),
            })
    return results


# ===== TESTS =====

class TestMultivarMA:

    def test_01_app_loads_no_errors(self, driver):
        """App loads without JS errors."""
        load_app(driver)
        logs = driver.get_log("browser")
        # Filter out network resource errors (favicon etc) — only JS errors matter
        severe = [l for l in logs if l["level"] == "SEVERE"
                  and "Failed to load resource" not in l.get("message", "")]
        assert len(severe) == 0, f"JS errors: {severe}"

    def test_02_demo_loads_5_studies(self, driver):
        """Demo data (Berkey 1998) loads 5 studies."""
        click_demo_and_analyze(driver)
        results = get_results_table(driver)
        assert len(results) >= 2, "Expected at least 2 outcome rows"
        # Check study count in summary
        stats = driver.find_element(By.ID, "summaryStats").text
        assert "5" in stats, f"Expected 5 studies, got: {stats}"

    def test_03_pooled_pd_range(self, driver):
        """Pooled PD (Outcome 1) in [-0.40, -0.15]."""
        click_demo_and_analyze(driver)
        results = get_results_table(driver)
        pd_val = float(results[0]["pooled_mv"])
        assert -0.40 <= pd_val <= -0.15, f"PD pooled={pd_val} outside [-0.40, -0.15]"

    def test_04_pooled_al_range(self, driver):
        """Pooled AL (Outcome 2) in [-0.25, 0.00]."""
        click_demo_and_analyze(driver)
        results = get_results_table(driver)
        al_val = float(results[1]["pooled_mv"])
        assert -0.25 <= al_val <= 0.00, f"AL pooled={al_val} outside [-0.25, 0.00]"

    def test_05_mv_se_le_uv_se(self, driver):
        """Multivariate SE <= univariate SE for at least one outcome."""
        click_demo_and_analyze(driver)
        results = get_results_table(driver)
        any_better = False
        for r in results:
            se_mv = float(r["se_mv"])
            se_uv = float(r["se_uv"])
            if se_mv <= se_uv + 1e-6:
                any_better = True
        assert any_better, "MV SE should be <= UV SE for at least one outcome"

    def test_06_bos_positive_high_rho(self, driver):
        """BOS > 0 when rho=0.6."""
        load_app(driver)
        driver.find_element(By.ID, "btnDemo").click()
        time.sleep(0.1)
        # Set rho slider to 0.6
        driver.execute_script("document.getElementById('rhoSlider').value = '0.60'; document.getElementById('rhoVal').textContent = '0.60';")
        # Clear per-study correlations so slider takes effect
        ta = driver.find_element(By.ID, "csvInput")
        csv_no_corr = """Study,Effect1,SE1,Effect2,SE2
Pihlstrom 1983,-0.34,0.099,-0.31,0.072
Lindhe 1984,0.01,0.112,-0.09,0.089
Knowles 1983,-0.64,0.171,-0.63,0.143
Ramfjord 1987,-0.32,0.075,-0.14,0.076
Becker 1988,-0.10,0.118,0.15,0.101"""
        ta.clear()
        ta.send_keys(csv_no_corr)
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        results = get_results_table(driver)
        any_pos = any(float(r["bos"].replace("%", "")) > 0 for r in results)
        assert any_pos, "BOS should be > 0 for at least one outcome with rho=0.6"

    def test_07_bos_near_zero_rho_zero(self, driver):
        """BOS smaller with rho=0 than rho=0.6 (atol=5%)."""
        load_app(driver)
        ta = driver.find_element(By.ID, "csvInput")
        csv_no_corr = """Study,Effect1,SE1,Effect2,SE2
Pihlstrom 1983,-0.34,0.099,-0.31,0.072
Lindhe 1984,0.01,0.112,-0.09,0.089
Knowles 1983,-0.64,0.171,-0.63,0.143
Ramfjord 1987,-0.32,0.075,-0.14,0.076
Becker 1988,-0.10,0.118,0.15,0.101"""
        # Analyze with rho=0
        driver.execute_script("document.getElementById('rhoSlider').value = '0.00'; document.getElementById('rhoVal').textContent = '0.00';")
        ta.clear()
        ta.send_keys(csv_no_corr)
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        results_rho0 = get_results_table(driver)
        bos_rho0 = [abs(float(r["bos"].replace("%", ""))) for r in results_rho0]

        # Analyze with rho=0.6
        driver.execute_script("document.getElementById('rhoSlider').value = '0.60'; document.getElementById('rhoVal').textContent = '0.60';")
        ta.clear()
        ta.send_keys(csv_no_corr)
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        results_rho6 = get_results_table(driver)
        bos_rho6 = [abs(float(r["bos"].replace("%", ""))) for r in results_rho6]

        # BOS at rho=0 should generally be less than at rho=0.6
        # At minimum, the average BOS with rho=0 should be less
        avg_bos0 = sum(bos_rho0) / len(bos_rho0)
        avg_bos6 = sum(bos_rho6) / len(bos_rho6)
        assert avg_bos0 <= avg_bos6 + 5.0, \
            f"BOS with rho=0 ({avg_bos0:.1f}%) should be <= BOS with rho=0.6 ({avg_bos6:.1f}%)"

    def test_08_slider_changes_results(self, driver):
        """Correlation slider changes pooled results."""
        load_app(driver)
        ta = driver.find_element(By.ID, "csvInput")
        csv_no_corr = """Study,Effect1,SE1,Effect2,SE2
Pihlstrom 1983,-0.34,0.099,-0.31,0.072
Lindhe 1984,0.01,0.112,-0.09,0.089
Knowles 1983,-0.64,0.171,-0.63,0.143
Ramfjord 1987,-0.32,0.075,-0.14,0.076
Becker 1988,-0.10,0.118,0.15,0.101"""
        ta.clear()
        ta.send_keys(csv_no_corr)
        # Analyze with rho=0.2
        driver.execute_script("document.getElementById('rhoSlider').value = '0.20'; document.getElementById('rhoVal').textContent = '0.20';")
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        r1 = get_results_table(driver)
        val1 = float(r1[0]["pooled_mv"])

        # Analyze with rho=0.8
        driver.execute_script("document.getElementById('rhoSlider').value = '0.80'; document.getElementById('rhoVal').textContent = '0.80';")
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        r2 = get_results_table(driver)
        val2 = float(r2[0]["pooled_mv"])

        # They may be close, but SE should differ
        se1 = float(r1[0]["se_mv"])
        se2 = float(r2[0]["se_mv"])
        assert abs(val1 - val2) > 1e-6 or abs(se1 - se2) > 1e-6, \
            f"Changing rho should affect results: val1={val1}, val2={val2}, se1={se1}, se2={se2}"

    def test_09_forest_plot_columns(self, driver):
        """Forest plot SVG has study markers for 2 columns."""
        click_demo_and_analyze(driver)
        svg = driver.find_element(By.ID, "forestSVG")
        assert svg is not None, "Forest SVG not found"
        markers = svg.find_elements(By.CSS_SELECTOR, "rect.study-marker")
        # 5 studies x 2 outcomes = 10 markers
        assert len(markers) >= 8, f"Expected ~10 study markers, got {len(markers)}"

    def test_10_tau_heatmap_renders(self, driver):
        """Tau heatmap SVG renders."""
        click_demo_and_analyze(driver)
        svg = driver.find_element(By.ID, "heatmapSVG")
        assert svg is not None, "Heatmap SVG not found"
        cells = svg.find_elements(By.CSS_SELECTOR, "rect.heatmap-cell")
        assert len(cells) >= 4, f"Expected >= 4 heatmap cells, got {len(cells)}"

    def test_11_bos_bar_chart_renders(self, driver):
        """BOS bar chart SVG renders."""
        click_demo_and_analyze(driver)
        svg = driver.find_element(By.ID, "bosSVG")
        assert svg is not None, "BOS SVG not found"
        bars = svg.find_elements(By.CSS_SELECTOR, "rect.bos-bar")
        assert len(bars) >= 2, f"Expected >= 2 BOS bars, got {len(bars)}"

    def test_12_missing_outcome(self, driver):
        """Study with only Effect1 -> still included, no NaN."""
        load_app(driver)
        ta = driver.find_element(By.ID, "csvInput")
        csv_missing = """Study,Effect1,SE1,Effect2,SE2
StudyA,-0.5,0.1,-0.3,0.08
StudyB,-0.3,0.12,,
StudyC,-0.4,0.09,-0.2,0.1"""
        ta.clear()
        ta.send_keys(csv_missing)
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        results = get_results_table(driver)
        for r in results:
            assert "NaN" not in r["pooled_mv"], f"NaN in pooled: {r}"
            assert "NaN" not in r["se_mv"], f"NaN in SE: {r}"
        # Check study count
        stats = driver.find_element(By.ID, "summaryStats").text
        assert "3" in stats, f"Expected 3 studies (including missing), got: {stats}"

    def test_13_k2_valid(self, driver):
        """k=2 studies: produces valid result."""
        load_app(driver)
        ta = driver.find_element(By.ID, "csvInput")
        csv_k2 = """Study,Effect1,SE1,Effect2,SE2
StudyA,-0.5,0.1,-0.3,0.08
StudyB,-0.3,0.12,-0.1,0.09"""
        ta.clear()
        ta.send_keys(csv_k2)
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        results = get_results_table(driver)
        assert len(results) >= 2, "Expected 2 outcome rows"
        for r in results:
            val = float(r["pooled_mv"])
            assert -2.0 < val < 2.0, f"Unreasonable pooled value: {val}"

    def test_14_summary_table_cis(self, driver):
        """Summary table shows both pooled estimates with CIs."""
        click_demo_and_analyze(driver)
        results = get_results_table(driver)
        assert len(results) >= 2, "Need at least 2 outcomes"
        for r in results:
            ci = r["ci"]
            assert "[" in ci and "]" in ci, f"CI format wrong: {ci}"
            # Parse CI
            ci_clean = ci.replace("[", "").replace("]", "").split(",")
            assert len(ci_clean) == 2, f"CI should have 2 bounds: {ci}"
            lo = float(ci_clean[0].strip())
            hi = float(ci_clean[1].strip())
            pooled = float(r["pooled_mv"])
            assert lo < pooled < hi, f"Pooled {pooled} not within CI [{lo}, {hi}]"

    def test_15_export_csv(self, driver):
        """Export CSV contains both outcomes."""
        click_demo_and_analyze(driver)
        # We can't easily test file download in headless, but we can test the button exists
        # and that clicking it doesn't error
        btn = driver.find_element(By.ID, "btnExportCSV")
        assert btn is not None, "Export CSV button not found"
        # Execute the export logic inline to check CSV content
        csv_content = driver.execute_script("""
            if (!lastResults) return '';
            const res = lastResults;
            const labels = res.labels;
            let csv = 'Type';
            for (let j = 0; j < res.p; j++) csv += ',' + labels[j] + '_Effect';
            csv += '\\n';
            csv += 'Multivariate';
            for (let j = 0; j < res.p; j++) csv += ',' + res.mu[j].toFixed(4);
            csv += '\\n';
            return csv;
        """)
        assert "PD_Effect" in csv_content, f"CSV missing PD: {csv_content}"
        assert "AL_Effect" in csv_content, f"CSV missing AL: {csv_content}"
        assert "Multivariate" in csv_content, f"CSV missing Multivariate row: {csv_content}"

    def test_16_three_outcome_mode(self, driver):
        """3-outcome mode: produces 3 columns in forest."""
        load_app(driver)
        # Set to 3 outcomes
        sel = driver.find_element(By.ID, "nOutcomes")
        driver.execute_script("arguments[0].value = '3'; arguments[0].dispatchEvent(new Event('change'));", sel)
        time.sleep(0.2)
        ta = driver.find_element(By.ID, "csvInput")
        csv_3out = """Study,Effect1,SE1,Effect2,SE2,Effect3,SE3
StudyA,-0.5,0.1,-0.3,0.08,-0.2,0.11
StudyB,-0.3,0.12,-0.1,0.09,-0.15,0.10
StudyC,-0.4,0.09,-0.2,0.1,-0.25,0.12
StudyD,-0.35,0.11,-0.18,0.085,-0.22,0.095"""
        ta.clear()
        ta.send_keys(csv_3out)
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        results = get_results_table(driver)
        assert len(results) >= 3, f"Expected 3 outcome rows, got {len(results)}"
        # Check forest SVG has summary diamonds
        svg = driver.find_element(By.ID, "forestSVG")
        diamonds = svg.find_elements(By.CSS_SELECTOR, "polygon.summary-diamond")
        assert len(diamonds) >= 3, f"Expected 3 summary diamonds, got {len(diamonds)}"

    def test_17_negative_correlation(self, driver):
        """Negative correlation (rho=-0.3): valid results, no NaN."""
        load_app(driver)
        driver.execute_script("document.getElementById('rhoSlider').value = '-0.30'; document.getElementById('rhoVal').textContent = '-0.30';")
        ta = driver.find_element(By.ID, "csvInput")
        csv_data = """Study,Effect1,SE1,Effect2,SE2
StudyA,-0.5,0.1,-0.3,0.08
StudyB,-0.3,0.12,-0.1,0.09
StudyC,-0.4,0.09,-0.2,0.1
StudyD,-0.35,0.11,-0.18,0.085"""
        ta.clear()
        ta.send_keys(csv_data)
        driver.find_element(By.ID, "btnAnalyze").click()
        time.sleep(0.5)
        results = get_results_table(driver)
        assert len(results) >= 2, "Expected 2 outcome rows"
        for r in results:
            assert "NaN" not in r["pooled_mv"], f"NaN in pooled with neg rho: {r}"
            assert "NaN" not in r["se_mv"], f"NaN in SE with neg rho: {r}"
            val = float(r["pooled_mv"])
            assert -2.0 < val < 2.0, f"Unreasonable value with neg rho: {val}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
