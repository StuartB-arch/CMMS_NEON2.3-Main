"""
KPI Trend Analyzer Module
Provides trend analysis, forecasting, and alerting for KPIs including:
- Historical trend analysis
- Target comparison
- Alert generation for KPIs below target
- Trend visualization
- Predictive insights
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import statistics


class KPITrendAnalyzer:
    """Analyzes KPI trends and generates alerts"""

    def __init__(self, conn):
        """
        Initialize trend analyzer

        Args:
            conn: Database connection
        """
        self.conn = conn

        # Define target values for each KPI (can be customized)
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
        cursor = self.conn.cursor()

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
            # Use linear regression approximation
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

        # Calculate volatility (standard deviation)
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

            # Check for improving trend (for KPIs where lower is better)
            if target_info.get('direction') == 'lower' and analysis['trend'] == 'improving':
                # This is actually bad for "lower is better" KPIs
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
            if analysis['volatility'] > analysis['average_value'] * 0.3:  # Volatility > 30% of average
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

    def export_trend_report(self, filename: str = None) -> str:
        """
        Export trend analysis report

        Args:
            filename: Optional filename for export

        Returns:
            Report text or filename
        """
        if filename is None:
            filename = f"kpi_trend_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"KPI TREND ANALYSIS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Dashboard summary
        summary = self.get_kpi_dashboard_summary()
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
        alerts = self.generate_alerts(months=6)
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

        for kpi_name in self.kpi_targets.keys():
            analysis = self.analyze_trend(kpi_name, months=12)

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

        report_text = "\n".join(report_lines)

        # Save to file if requested
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(report_text)
                return filename
            except Exception as e:
                print(f"Error saving report: {e}")

        return report_text


class KPITrendViewer:
    """GUI for viewing KPI trends and alerts"""

    def __init__(self, parent, conn):
        """
        Initialize trend viewer window

        Args:
            parent: Parent tkinter window
            conn: Database connection
        """
        self.conn = conn
        self.analyzer = KPITrendAnalyzer(conn)

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("KPI Trends & Alerts")
        self.window.geometry("1200x800")

        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        """Create user interface"""
        # Header
        header_frame = ttk.Frame(self.window)
        header_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(header_frame, text="KPI Trends & Alerts",
                 font=('Arial', 14, 'bold')).pack(side='left')

        ttk.Button(header_frame, text="Refresh",
                  command=self._load_data).pack(side='right', padx=5)

        ttk.Button(header_frame, text="Export Report",
                  command=self._export_report).pack(side='right', padx=5)

        # Notebook for different views
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # Alerts tab
        alerts_frame = ttk.Frame(notebook)
        notebook.add(alerts_frame, text="Alerts")
        self._create_alerts_view(alerts_frame)

        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="Dashboard")
        self._create_dashboard_view(dashboard_frame)

        # Trends tab
        trends_frame = ttk.Frame(notebook)
        notebook.add(trends_frame, text="Detailed Trends")
        self._create_trends_view(trends_frame)

    def _create_alerts_view(self, parent):
        """Create alerts view"""
        # Alert list
        scroll_frame = ttk.Frame(parent)
        scroll_frame.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(scroll_frame)
        scrollbar.pack(side='right', fill='y')

        self.alerts_tree = ttk.Treeview(scroll_frame,
                                        columns=('Severity', 'KPI', 'Type', 'Message'),
                                        show='headings',
                                        yscrollcommand=scrollbar.set)
        self.alerts_tree.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.alerts_tree.yview)

        # Configure columns
        self.alerts_tree.heading('Severity', text='Severity')
        self.alerts_tree.heading('KPI', text='KPI')
        self.alerts_tree.heading('Type', text='Alert Type')
        self.alerts_tree.heading('Message', text='Message')

        self.alerts_tree.column('Severity', width=100)
        self.alerts_tree.column('KPI', width=250)
        self.alerts_tree.column('Type', width=150)
        self.alerts_tree.column('Message', width=500)

    def _create_dashboard_view(self, parent):
        """Create dashboard summary view"""
        self.dashboard_text = tk.Text(parent, wrap='word', font=('Courier', 10))
        self.dashboard_text.pack(fill='both', expand=True, padx=10, pady=10)

    def _create_trends_view(self, parent):
        """Create detailed trends view"""
        # KPI selector
        selector_frame = ttk.Frame(parent)
        selector_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(selector_frame, text="Select KPI:").pack(side='left', padx=5)

        self.kpi_var = tk.StringVar()
        self.kpi_combo = ttk.Combobox(selector_frame, textvariable=self.kpi_var,
                                      width=40, state='readonly')
        self.kpi_combo.pack(side='left', padx=5)
        self.kpi_combo.bind('<<ComboboxSelected>>', lambda e: self._show_kpi_detail())

        # Detail display
        self.trend_text = tk.Text(parent, wrap='word', font=('Courier', 10))
        self.trend_text.pack(fill='both', expand=True, padx=10, pady=10)

    def _load_data(self):
        """Load and display all data"""
        try:
            # Load alerts
            alerts = self.analyzer.generate_alerts(months=6)

            # Clear alerts tree
            for item in self.alerts_tree.get_children():
                self.alerts_tree.delete(item)

            # Populate alerts
            for alert in alerts:
                # Color code by severity
                if alert['severity'] == 'high':
                    tag = 'high'
                elif alert['severity'] == 'medium':
                    tag = 'medium'
                else:
                    tag = 'low'

                self.alerts_tree.insert('', 'end',
                                       values=(alert['severity'].upper(),
                                              alert['kpi_name'],
                                              alert['alert_type'],
                                              alert['message']),
                                       tags=(tag,))

            # Configure tags
            self.alerts_tree.tag_configure('high', background='#ffcccc')
            self.alerts_tree.tag_configure('medium', background='#ffffcc')
            self.alerts_tree.tag_configure('low', background='#ccffcc')

            # Load dashboard
            summary = self.analyzer.get_kpi_dashboard_summary()
            self._display_dashboard(summary)

            # Populate KPI selector
            kpi_names = list(self.analyzer.kpi_targets.keys())
            self.kpi_combo['values'] = kpi_names
            if kpi_names:
                self.kpi_combo.current(0)
                self._show_kpi_detail()

        except Exception as e:
            messagebox.showerror("Error", f"Error loading data: {str(e)}")

    def _display_dashboard(self, summary: Dict):
        """Display dashboard summary"""
        self.dashboard_text.delete('1.0', 'end')

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

        self.dashboard_text.insert('1.0', text)

    def _show_kpi_detail(self):
        """Show detailed analysis for selected KPI"""
        kpi_name = self.kpi_var.get()
        if not kpi_name:
            return

        analysis = self.analyzer.analyze_trend(kpi_name, months=12)

        self.trend_text.delete('1.0', 'end')

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

        self.trend_text.insert('1.0', text)

    def _export_report(self):
        """Export trend report"""
        try:
            filename = self.analyzer.export_trend_report()
            messagebox.showinfo("Export Complete",
                              f"Trend report exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting report:\n{str(e)}")


def show_kpi_trends(parent, conn):
    """
    Show KPI trends viewer window

    Args:
        parent: Parent tkinter window
        conn: Database connection
    """
    KPITrendViewer(parent, conn)
