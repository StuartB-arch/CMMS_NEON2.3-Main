"""
KPI Trend Analyzer Tab - PyQt5 Implementation
Provides trend analysis, forecasting, and alerting for KPIs
Complete port from Tkinter to PyQt5

Features:
- Historical trend analysis
- Target comparison and alerts
- Trend visualization with matplotlib
- Export to PDF/CSV
- Dashboard summary view
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QGroupBox, QComboBox,
    QTabWidget, QTextEdit, QFrame, QAbstractItemView, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
from psycopg2 import extras
import statistics
import csv

# Matplotlib imports for charts
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not available. Charts will not be displayed.")


class KPITrendAnalyzer:
    """Analyzes KPI trends and generates alerts"""

    def __init__(self, conn):
        """
        Initialize trend analyzer

        Args:
            conn: Database connection
        """
        self.conn = conn

        # Define target values for each KPI
        self.kpi_targets = {
            'PM Adherence': {'target': 90, 'direction': 'higher', 'unit': '%'},
            'Work Orders Opened': {'target': None, 'direction': 'neutral', 'unit': 'count'},
            'Work Orders Closed': {'target': None, 'direction': 'higher', 'unit': 'count'},
            'Work Order Backlog': {'target': 20, 'direction': 'lower', 'unit': 'count'},
            'Technical Availability': {'target': 95, 'direction': 'higher', 'unit': '%'},
            'Mean Time Between Failures (MTBF)': {'target': 720, 'direction': 'higher', 'unit': 'hours'},
            'Mean Time To Repair (MTTR)': {'target': 8, 'direction': 'lower', 'unit': 'hours'},
            'Total Maintenance Labor Hours': {'target': None, 'direction': 'neutral', 'unit': 'hours'},
            'Injury Frequency Rate': {'target': 0, 'direction': 'lower', 'unit': 'rate'},
            'Near Miss Reports': {'target': None, 'direction': 'higher', 'unit': 'count'}
        }

    def get_kpi_history(self, kpi_name: str, months: int = 12) -> List[Dict]:
        """
        Get historical KPI data

        Args:
            kpi_name: KPI name
            months: Number of months to retrieve

        Returns:
            List of historical data points
        """
        cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

        # Calculate start period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        start_period = start_date.strftime('%Y-%m')

        cursor.execute('''
            SELECT measurement_period, data_field, data_value, data_text,
                   entered_date, entered_by
            FROM kpi_manual_data
            WHERE kpi_name = %s
            AND measurement_period >= %s
            ORDER BY measurement_period ASC
        ''', (kpi_name, start_period))

        # Group by period
        history = defaultdict(dict)
        for row in cursor.fetchall():
            period = row[0]
            field = row[1]
            value = row[2]
            text = row[3]
            date = row[4]
            user = row[5]

            if field == 'value':
                history[period]['value'] = float(value) if value else None
                history[period]['period'] = period
                history[period]['entered_date'] = date
                history[period]['entered_by'] = user
            else:
                history[period][field] = value or text

        # Convert to list and sort
        result = sorted(history.values(), key=lambda x: x.get('period', ''))

        return result

    def analyze_trend(self, kpi_name: str, months: int = 6) -> Dict:
        """
        Analyze trend for a KPI

        Args:
            kpi_name: KPI name
            months: Number of months to analyze

        Returns:
            Dictionary with trend analysis
        """
        history = self.get_kpi_history(kpi_name, months)

        if not history:
            return {
                'kpi_name': kpi_name,
                'trend': 'no_data',
                'message': 'No historical data available'
            }

        # Extract values
        values = [h['value'] for h in history if h.get('value') is not None]

        if len(values) < 2:
            return {
                'kpi_name': kpi_name,
                'trend': 'insufficient_data',
                'message': 'Insufficient data for trend analysis',
                'data_points': len(values)
            }

        # Calculate statistics
        avg_value = statistics.mean(values)
        latest_value = values[-1]

        # Calculate trend direction
        if len(values) >= 3:
            recent_avg = statistics.mean(values[-3:])
            older_avg = statistics.mean(values[:3])

            if recent_avg > older_avg * 1.05:  # 5% threshold
                trend_direction = 'improving'
            elif recent_avg < older_avg * 0.95:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'
        else:
            trend_direction = 'stable'

        # Calculate volatility
        volatility = statistics.stdev(values) if len(values) > 1 else 0

        # Get target information
        target_info = self.kpi_targets.get(kpi_name, {})
        target_value = target_info.get('target')

        # Check if meeting target
        meets_target = None
        target_gap = None
        if target_value is not None:
            direction = target_info.get('direction', 'higher')
            if direction == 'higher':
                meets_target = latest_value >= target_value
                target_gap = latest_value - target_value
            elif direction == 'lower':
                meets_target = latest_value <= target_value
                target_gap = target_value - latest_value
            else:
                meets_target = True
                target_gap = 0

        return {
            'kpi_name': kpi_name,
            'trend': trend_direction,
            'latest_value': latest_value,
            'average_value': round(avg_value, 2),
            'min_value': min(values),
            'max_value': max(values),
            'volatility': round(volatility, 2),
            'data_points': len(values),
            'periods': [h.get('period') for h in history],
            'values': values,
            'target_value': target_value,
            'meets_target': meets_target,
            'target_gap': round(target_gap, 2) if target_gap is not None else None,
            'unit': target_info.get('unit', '')
        }

    def generate_alerts(self, months: int = 3) -> List[Dict]:
        """
        Generate alerts for KPIs below target or showing negative trends

        Args:
            months: Number of months to analyze

        Returns:
            List of alert dictionaries
        """
        alerts = []

        # Analyze all tracked KPIs
        for kpi_name in self.kpi_targets.keys():
            analysis = self.analyze_trend(kpi_name, months)

            if analysis['trend'] in ['no_data', 'insufficient_data']:
                continue

            # Check if below target
            if analysis['meets_target'] is False:
                severity = 'high' if abs(analysis['target_gap']) > analysis['target_value'] * 0.2 else 'medium'

                alerts.append({
                    'kpi_name': kpi_name,
                    'alert_type': 'below_target',
                    'severity': severity,
                    'message': f"{kpi_name} is below target: {analysis['latest_value']} {analysis['unit']} (Target: {analysis['target_value']} {analysis['unit']})",
                    'gap': analysis['target_gap'],
                    'latest_value': analysis['latest_value'],
                    'target_value': analysis['target_value'],
                    'unit': analysis['unit']
                })

            # Check for declining trend (for KPIs where higher is better)
            target_info = self.kpi_targets.get(kpi_name, {})
            if target_info.get('direction') == 'higher' and analysis['trend'] == 'declining':
                alerts.append({
                    'kpi_name': kpi_name,
                    'alert_type': 'declining_trend',
                    'severity': 'medium',
                    'message': f"{kpi_name} shows declining trend: {analysis['latest_value']} {analysis['unit']}",
                    'latest_value': analysis['latest_value'],
                    'average_value': analysis['average_value'],
                    'unit': analysis['unit']
                })

            # Check for increasing trend (for KPIs where lower is better)
            if target_info.get('direction') == 'lower' and analysis['trend'] == 'improving':
                alerts.append({
                    'kpi_name': kpi_name,
                    'alert_type': 'increasing_trend',
                    'severity': 'medium',
                    'message': f"{kpi_name} is increasing: {analysis['latest_value']} {analysis['unit']} (Target: {analysis['target_value']} {analysis['unit']})",
                    'latest_value': analysis['latest_value'],
                    'target_value': analysis['target_value'],
                    'unit': analysis['unit']
                })

            # Check for high volatility
            if analysis['volatility'] > analysis['average_value'] * 0.3:
                alerts.append({
                    'kpi_name': kpi_name,
                    'alert_type': 'high_volatility',
                    'severity': 'low',
                    'message': f"{kpi_name} shows high volatility: ±{analysis['volatility']} {analysis['unit']}",
                    'volatility': analysis['volatility'],
                    'average_value': analysis['average_value'],
                    'unit': analysis['unit']
                })

        # Sort alerts by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 3))

        return alerts

    def get_kpi_dashboard_summary(self) -> Dict:
        """
        Get summary of all KPIs for dashboard

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total_kpis': len(self.kpi_targets),
            'meeting_target': 0,
            'below_target': 0,
            'no_target': 0,
            'no_data': 0,
            'trending_up': 0,
            'trending_down': 0,
            'stable': 0,
            'kpi_status': []
        }

        for kpi_name in self.kpi_targets.keys():
            analysis = self.analyze_trend(kpi_name, months=3)

            status = {
                'name': kpi_name,
                'trend': analysis['trend'],
                'latest_value': analysis.get('latest_value'),
                'meets_target': analysis.get('meets_target'),
                'unit': analysis.get('unit')
            }

            if analysis['trend'] in ['no_data', 'insufficient_data']:
                summary['no_data'] += 1
                status['status'] = 'no_data'
            elif analysis.get('meets_target') is None:
                summary['no_target'] += 1
                status['status'] = 'no_target'
            elif analysis['meets_target']:
                summary['meeting_target'] += 1
                status['status'] = 'meeting_target'
            else:
                summary['below_target'] += 1
                status['status'] = 'below_target'

            # Count trends
            if analysis['trend'] == 'improving':
                summary['trending_up'] += 1
            elif analysis['trend'] == 'declining':
                summary['trending_down'] += 1
            elif analysis['trend'] == 'stable':
                summary['stable'] += 1

            summary['kpi_status'].append(status)

        return summary


class KPITrendAnalyzerTab(QWidget):
    """Tab for viewing KPI trends and alerts"""

    status_updated = pyqtSignal(str)

    def __init__(self, conn, parent=None):
        """
        Initialize KPI Trend Analyzer Tab

        Args:
            conn: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.conn = conn
        self.analyzer = KPITrendAnalyzer(conn)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Header Section
        header_frame = self.create_header()
        layout.addWidget(header_frame)

        # Tab Widget for different views
        self.tab_widget = QTabWidget()

        # Alerts Tab
        alerts_tab = self.create_alerts_tab()
        self.tab_widget.addTab(alerts_tab, "Alerts")

        # Dashboard Tab
        dashboard_tab = self.create_dashboard_tab()
        self.tab_widget.addTab(dashboard_tab, "Dashboard")

        # Detailed Trends Tab
        trends_tab = self.create_trends_tab()
        self.tab_widget.addTab(trends_tab, "Detailed Trends")

        # Charts Tab (if matplotlib available)
        if MATPLOTLIB_AVAILABLE:
            charts_tab = self.create_charts_tab()
            self.tab_widget.addTab(charts_tab, "Charts")

        layout.addWidget(self.tab_widget)

        self.setLayout(layout)

    def create_header(self):
        """Create header section"""
        frame = QFrame()
        layout = QHBoxLayout()

        # Title
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label = QLabel("KPI Trends & Alerts")
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        layout.addStretch()

        # Refresh Button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(refresh_btn)

        # Export Report Button
        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(self.export_report)
        layout.addWidget(export_btn)

        # Export CSV Button
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.export_to_csv)
        layout.addWidget(export_csv_btn)

        frame.setLayout(layout)
        return frame

    def create_alerts_tab(self):
        """Create alerts view tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Alerts Table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(4)
        self.alerts_table.setHorizontalHeaderLabels(['Severity', 'KPI', 'Type', 'Message'])

        header = self.alerts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.alerts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.alerts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.alerts_table.setAlternatingRowColors(True)

        layout.addWidget(self.alerts_table)
        widget.setLayout(layout)
        return widget

    def create_dashboard_tab(self):
        """Create dashboard summary tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Dashboard Text Display
        self.dashboard_text = QTextEdit()
        self.dashboard_text.setReadOnly(True)
        self.dashboard_text.setFont(QFont('Courier', 10))

        layout.addWidget(self.dashboard_text)
        widget.setLayout(layout)
        return widget

    def create_trends_tab(self):
        """Create detailed trends tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # KPI Selector
        selector_frame = QFrame()
        selector_layout = QHBoxLayout()

        selector_layout.addWidget(QLabel("Select KPI:"))

        self.kpi_combo = QComboBox()
        self.kpi_combo.currentTextChanged.connect(self.show_kpi_detail)
        selector_layout.addWidget(self.kpi_combo)

        selector_layout.addStretch()
        selector_frame.setLayout(selector_layout)
        layout.addWidget(selector_frame)

        # Trend Detail Text
        self.trend_text = QTextEdit()
        self.trend_text.setReadOnly(True)
        self.trend_text.setFont(QFont('Courier', 10))

        layout.addWidget(self.trend_text)
        widget.setLayout(layout)
        return widget

    def create_charts_tab(self):
        """Create charts tab with matplotlib"""
        widget = QWidget()
        layout = QVBoxLayout()

        # KPI Selector for Charts
        selector_frame = QFrame()
        selector_layout = QHBoxLayout()

        selector_layout.addWidget(QLabel("Select KPI:"))

        self.chart_kpi_combo = QComboBox()
        self.chart_kpi_combo.currentTextChanged.connect(self.update_chart)
        selector_layout.addWidget(self.chart_kpi_combo)

        selector_layout.addStretch()
        selector_frame.setLayout(selector_layout)
        layout.addWidget(selector_frame)

        # Chart Canvas
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        widget.setLayout(layout)
        return widget

    def load_data(self):
        """Load and display all data"""
        try:
            # Load alerts
            alerts = self.analyzer.generate_alerts(months=6)

            # Clear alerts table
            self.alerts_table.setRowCount(0)

            # Populate alerts
            self.alerts_table.setRowCount(len(alerts))
            for row, alert in enumerate(alerts):
                # Severity
                severity_item = QTableWidgetItem(alert['severity'].upper())
                if alert['severity'] == 'high':
                    severity_item.setBackground(QColor('#ffcccc'))
                elif alert['severity'] == 'medium':
                    severity_item.setBackground(QColor('#ffffcc'))
                else:
                    severity_item.setBackground(QColor('#ccffcc'))
                self.alerts_table.setItem(row, 0, severity_item)

                # KPI, Type, Message
                self.alerts_table.setItem(row, 1, QTableWidgetItem(alert['kpi_name']))
                self.alerts_table.setItem(row, 2, QTableWidgetItem(alert['alert_type']))
                self.alerts_table.setItem(row, 3, QTableWidgetItem(alert['message']))

            # Load dashboard
            summary = self.analyzer.get_kpi_dashboard_summary()
            self.display_dashboard(summary)

            # Populate KPI selectors
            kpi_names = list(self.analyzer.kpi_targets.keys())
            self.kpi_combo.clear()
            self.kpi_combo.addItems(kpi_names)

            if MATPLOTLIB_AVAILABLE:
                self.chart_kpi_combo.clear()
                self.chart_kpi_combo.addItems(kpi_names)

            self.status_updated.emit(f"Loaded {len(alerts)} alerts")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")

    def display_dashboard(self, summary: Dict):
        """Display dashboard summary"""
        text = f"""
KPI DASHBOARD SUMMARY
{'=' * 80}

OVERALL STATUS:
  Total KPIs: {summary['total_kpis']}
  Meeting Target: {summary['meeting_target']}
  Below Target: {summary['below_target']}
  No Target Set: {summary['no_target']}
  No Data: {summary['no_data']}

TREND ANALYSIS:
  Improving: {summary['trending_up']}
  Declining: {summary['trending_down']}
  Stable: {summary['stable']}

{'=' * 80}
KPI STATUS:
{'=' * 80}

"""

        for kpi in summary['kpi_status']:
            status_symbol = {
                'meeting_target': '✓',
                'below_target': '✗',
                'no_target': '-',
                'no_data': '?'
            }.get(kpi['status'], '?')

            trend_symbol = {
                'improving': '↑',
                'declining': '↓',
                'stable': '→',
                'no_data': '?',
                'insufficient_data': '?'
            }.get(kpi['trend'], '?')

            value_str = f"{kpi['latest_value']} {kpi['unit']}" if kpi['latest_value'] is not None else "No data"

            text += f"{status_symbol} {trend_symbol} {kpi['name']:<40} {value_str}\n"

        self.dashboard_text.setPlainText(text)

    def show_kpi_detail(self):
        """Show detailed analysis for selected KPI"""
        kpi_name = self.kpi_combo.currentText()
        if not kpi_name:
            return

        analysis = self.analyzer.analyze_trend(kpi_name, months=12)

        if analysis['trend'] in ['no_data', 'insufficient_data']:
            text = f"\n{kpi_name}\n{'=' * 80}\n\n{analysis['message']}\n"
        else:
            text = f"""
{kpi_name}
{'=' * 80}

CURRENT STATUS:
  Latest Value: {analysis['latest_value']} {analysis['unit']}
  Trend: {analysis['trend'].upper()}
  Meets Target: {'Yes' if analysis['meets_target'] else 'No' if analysis['meets_target'] is not None else 'No target set'}

STATISTICS:
  Average: {analysis['average_value']} {analysis['unit']}
  Minimum: {analysis['min_value']} {analysis['unit']}
  Maximum: {analysis['max_value']} {analysis['unit']}
  Volatility: {analysis['volatility']} {analysis['unit']}
  Data Points: {analysis['data_points']}

TARGET COMPARISON:
  Target Value: {analysis['target_value']} {analysis['unit'] if analysis['target_value'] is not None else 'Not set'}
  Gap: {analysis['target_gap']} {analysis['unit'] if analysis['target_gap'] is not None else 'N/A'}

HISTORICAL VALUES:
"""
            # Add historical data
            for period, value in zip(analysis['periods'], analysis['values']):
                text += f"  {period}: {value} {analysis['unit']}\n"

        self.trend_text.setPlainText(text)

    def update_chart(self):
        """Update chart for selected KPI"""
        if not MATPLOTLIB_AVAILABLE:
            return

        kpi_name = self.chart_kpi_combo.currentText()
        if not kpi_name:
            return

        analysis = self.analyzer.analyze_trend(kpi_name, months=12)

        # Clear previous chart
        self.figure.clear()

        if analysis['trend'] in ['no_data', 'insufficient_data']:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, analysis['message'], ha='center', va='center', fontsize=14)
            ax.axis('off')
        else:
            ax = self.figure.add_subplot(111)

            # Plot data
            periods = analysis['periods']
            values = analysis['values']

            ax.plot(periods, values, marker='o', linewidth=2, markersize=8, label='Actual')

            # Plot target line if available
            if analysis['target_value'] is not None:
                ax.axhline(y=analysis['target_value'], color='r', linestyle='--', label='Target')

            # Plot average line
            ax.axhline(y=analysis['average_value'], color='g', linestyle=':', label='Average')

            ax.set_xlabel('Period', fontsize=12)
            ax.set_ylabel(f'{analysis["unit"]}', fontsize=12)
            ax.set_title(f'{kpi_name} - Trend Analysis', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Rotate x-axis labels for better readability
            ax.tick_params(axis='x', rotation=45)

        self.figure.tight_layout()
        self.canvas.draw()

    def export_report(self):
        """Export trend analysis report to text file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Trend Report",
                f"kpi_trend_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt)"
            )

            if not filename:
                return

            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append(f"KPI TREND ANALYSIS REPORT")
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("=" * 80)
            report_lines.append("")

            # Dashboard summary
            summary = self.analyzer.get_kpi_dashboard_summary()
            report_lines.append("DASHBOARD SUMMARY:")
            report_lines.append(f"  Total KPIs: {summary['total_kpis']}")
            report_lines.append(f"  Meeting Target: {summary['meeting_target']}")
            report_lines.append(f"  Below Target: {summary['below_target']}")
            report_lines.append(f"  No Target Set: {summary['no_target']}")
            report_lines.append(f"  No Data: {summary['no_data']}")
            report_lines.append("")
            report_lines.append(f"TRENDS:")
            report_lines.append(f"  Improving: {summary['trending_up']}")
            report_lines.append(f"  Declining: {summary['trending_down']}")
            report_lines.append(f"  Stable: {summary['stable']}")
            report_lines.append("")

            # Alerts
            alerts = self.analyzer.generate_alerts(months=6)
            if alerts:
                report_lines.append("=" * 80)
                report_lines.append("ALERTS:")
                report_lines.append("=" * 80)
                report_lines.append("")

                for alert in alerts:
                    report_lines.append(f"[{alert['severity'].upper()}] {alert['kpi_name']}")
                    report_lines.append(f"  Type: {alert['alert_type']}")
                    report_lines.append(f"  Message: {alert['message']}")
                    report_lines.append("")

            # Detailed KPI Analysis
            report_lines.append("=" * 80)
            report_lines.append("DETAILED KPI ANALYSIS:")
            report_lines.append("=" * 80)
            report_lines.append("")

            for kpi_name in self.analyzer.kpi_targets.keys():
                analysis = self.analyzer.analyze_trend(kpi_name, months=12)

                report_lines.append(f"\n{kpi_name}:")
                report_lines.append("-" * 40)

                if analysis['trend'] in ['no_data', 'insufficient_data']:
                    report_lines.append(f"  Status: {analysis['message']}")
                else:
                    report_lines.append(f"  Latest Value: {analysis['latest_value']} {analysis['unit']}")
                    report_lines.append(f"  Average: {analysis['average_value']} {analysis['unit']}")
                    report_lines.append(f"  Range: {analysis['min_value']} - {analysis['max_value']} {analysis['unit']}")
                    report_lines.append(f"  Trend: {analysis['trend']}")
                    report_lines.append(f"  Volatility: {analysis['volatility']} {analysis['unit']}")

                    if analysis['target_value'] is not None:
                        report_lines.append(f"  Target: {analysis['target_value']} {analysis['unit']}")
                        report_lines.append(f"  Meets Target: {'Yes' if analysis['meets_target'] else 'No'}")
                        if analysis['target_gap'] is not None:
                            report_lines.append(f"  Gap: {analysis['target_gap']} {analysis['unit']}")

                    report_lines.append(f"  Data Points: {analysis['data_points']}")

                report_lines.append("")

            # Save to file
            with open(filename, 'w') as f:
                f.write("\n".join(report_lines))

            QMessageBox.information(self, "Export Complete", f"Trend report exported to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting report:\n{str(e)}")

    def export_to_csv(self):
        """Export KPI data to CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export to CSV",
                f"kpi_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )

            if not filename:
                return

            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # Write header
                writer.writerow([
                    'KPI Name', 'Latest Value', 'Unit', 'Trend', 'Average',
                    'Min', 'Max', 'Volatility', 'Target', 'Meets Target', 'Gap'
                ])

                # Write data for each KPI
                for kpi_name in self.analyzer.kpi_targets.keys():
                    analysis = self.analyzer.analyze_trend(kpi_name, months=12)

                    if analysis['trend'] not in ['no_data', 'insufficient_data']:
                        writer.writerow([
                            kpi_name,
                            analysis['latest_value'],
                            analysis['unit'],
                            analysis['trend'],
                            analysis['average_value'],
                            analysis['min_value'],
                            analysis['max_value'],
                            analysis['volatility'],
                            analysis['target_value'] if analysis['target_value'] is not None else 'N/A',
                            'Yes' if analysis['meets_target'] else 'No' if analysis['meets_target'] is not None else 'N/A',
                            analysis['target_gap'] if analysis['target_gap'] is not None else 'N/A'
                        ])

            QMessageBox.information(self, "Export Complete", f"KPI data exported to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting to CSV:\n{str(e)}")


# Convenience function for compatibility
def show_kpi_trends(conn, parent=None):
    """
    Show KPI trends viewer as a standalone widget

    Args:
        conn: Database connection
        parent: Parent widget

    Returns:
        Widget instance
    """
    widget = KPITrendAnalyzerTab(conn, parent)
    return widget
