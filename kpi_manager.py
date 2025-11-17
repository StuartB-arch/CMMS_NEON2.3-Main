"""
KPI Manager Module
Handles KPI calculations, data management, and reporting for 2025 KPIs
"""

import psycopg2
from psycopg2 import extras
from datetime import datetime, timedelta
from decimal import Decimal
import calendar


class KPIManager:
    """Manages KPI calculations and data"""

    def __init__(self, pool):
        """Initialize with database connection pool"""
        self.pool = pool

    def get_all_kpi_definitions(self):
        """Get all active KPI definitions"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM kpi_definitions
                WHERE is_active = TRUE
                ORDER BY function_code, kpi_name
            """)
            results = cursor.fetchall()
            cursor.close()
            return results
        finally:
            self.pool.return_connection(conn)

    def get_kpi_by_name(self, kpi_name):
        """Get specific KPI definition"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM kpi_definitions
                WHERE kpi_name = %s AND is_active = TRUE
            """, (kpi_name,))
            result = cursor.fetchone()
            cursor.close()
            return result
        finally:
            self.pool.return_connection(conn)

    def save_manual_data(self, kpi_name, measurement_period, data_field, data_value,
                        data_text=None, notes=None, entered_by=None):
        """Save manual data input for KPI calculation"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO kpi_manual_data
                (kpi_name, measurement_period, data_field, data_value, data_text, notes, entered_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (kpi_name, measurement_period, data_field)
                DO UPDATE SET
                    data_value = EXCLUDED.data_value,
                    data_text = EXCLUDED.data_text,
                    notes = EXCLUDED.notes,
                    entered_by = EXCLUDED.entered_by,
                    entered_date = CURRENT_TIMESTAMP
            """, (kpi_name, measurement_period, data_field, data_value, data_text, notes, entered_by))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.return_connection(conn)

    def get_manual_data(self, kpi_name, measurement_period):
        """Get manual data for a specific KPI and period"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM kpi_manual_data
                WHERE kpi_name = %s AND measurement_period = %s
                ORDER BY data_field
            """, (kpi_name, measurement_period))
            results = cursor.fetchall()
            cursor.close()
            return results
        finally:
            self.pool.return_connection(conn)

    def save_kpi_result(self, kpi_name, measurement_period, calculated_value,
                       calculated_text=None, target_value=None, meets_criteria=None,
                       calculated_by=None, notes=None):
        """Save calculated KPI result"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO kpi_results
                (kpi_name, measurement_period, calculated_value, calculated_text,
                 target_value, meets_criteria, calculated_by, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (kpi_name, measurement_period)
                DO UPDATE SET
                    calculated_value = EXCLUDED.calculated_value,
                    calculated_text = EXCLUDED.calculated_text,
                    target_value = EXCLUDED.target_value,
                    meets_criteria = EXCLUDED.meets_criteria,
                    calculated_by = EXCLUDED.calculated_by,
                    notes = EXCLUDED.notes,
                    calculation_date = CURRENT_TIMESTAMP
            """, (kpi_name, measurement_period, calculated_value, calculated_text,
                  target_value, meets_criteria, calculated_by, notes))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.return_connection(conn)

    def get_kpi_results(self, measurement_period=None, kpi_name=None):
        """Get KPI results, optionally filtered by period and/or KPI name"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)

            query = """
                SELECT r.*, d.function_code, d.description, d.acceptance_criteria, d.frequency
                FROM kpi_results r
                JOIN kpi_definitions d ON r.kpi_name = d.kpi_name
                WHERE 1=1
            """
            params = []

            if measurement_period:
                query += " AND r.measurement_period = %s"
                params.append(measurement_period)

            if kpi_name:
                query += " AND r.kpi_name = %s"
                params.append(kpi_name)

            query += " ORDER BY d.function_code, r.kpi_name, r.measurement_period DESC"

            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        finally:
            self.pool.return_connection(conn)

    # ==================== KPI CALCULATION METHODS ====================

    def calculate_pm_adherence(self, measurement_period, username=None):
        """
        Calculate Preventive Maintenance Adherence
        Formula: (number of WO completed / number of WO scheduled) x 100%
        Target: >95%
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()

            # Parse period (format: YYYY-MM)
            year, month = map(int, measurement_period.split('-'))
            start_date = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day}"

            # Count scheduled PMs
            cursor.execute("""
                SELECT COUNT(*) FROM weekly_pm_schedules
                WHERE week_start_date::date >= %s::date AND week_start_date::date <= %s::date
            """, (start_date, end_date))
            scheduled = cursor.fetchone()[0]

            # Count completed PMs
            cursor.execute("""
                SELECT COUNT(*) FROM pm_completions
                WHERE completion_date::date >= %s::date AND completion_date::date <= %s::date
            """, (start_date, end_date))
            completed = cursor.fetchone()[0]

            cursor.close()

            # Calculate adherence
            if scheduled > 0:
                adherence = (completed / scheduled) * 100
                meets_criteria = adherence >= 95
            else:
                adherence = 0
                meets_criteria = None

            # Save result
            self.save_kpi_result(
                kpi_name='Preventive Maintenance Adherence',
                measurement_period=measurement_period,
                calculated_value=round(adherence, 2),
                calculated_text=f"{completed}/{scheduled} completed",
                target_value=95,
                meets_criteria=meets_criteria,
                calculated_by=username,
                notes=f"Scheduled: {scheduled}, Completed: {completed}"
            )

            return {
                'value': round(adherence, 2),
                'scheduled': scheduled,
                'completed': completed,
                'meets_criteria': meets_criteria
            }

        finally:
            self.pool.return_connection(conn)

    def calculate_wo_opened_vs_closed(self, measurement_period, username=None):
        """
        Calculate WO opened vs WO closed
        Formula: number of WO open vs number of WO closed
        Target: No >40 open WO
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()

            # Parse period
            year, month = map(int, measurement_period.split('-'))
            start_date = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day}"

            # Count opened CMs (CMs created in October)
            cursor.execute("""
                SELECT COUNT(*) FROM corrective_maintenance
                WHERE created_date::date >= %s::date AND created_date::date <= %s::date
            """, (start_date, end_date))
            opened = cursor.fetchone()[0]

            # Count closed CMs (CMs created in October that are now Closed/Completed)
            cursor.execute("""
                SELECT COUNT(*) FROM corrective_maintenance
                WHERE created_date::date >= %s::date AND created_date::date <= %s::date
                AND (status = 'Closed' OR status = 'Completed')
            """, (start_date, end_date))
            closed = cursor.fetchone()[0]

            # Count currently open CMs (CMs created in October that are still Open)
            cursor.execute("""
                SELECT COUNT(*) FROM corrective_maintenance
                WHERE created_date::date >= %s::date AND created_date::date <= %s::date
                AND status = 'Open'
            """, (start_date, end_date))
            currently_open = cursor.fetchone()[0]

            cursor.close()

            meets_criteria = currently_open <= 40

            # Save result
            self.save_kpi_result(
                kpi_name='WO opened vs WO closed',
                measurement_period=measurement_period,
                calculated_value=currently_open,
                calculated_text=f"Opened: {opened}, Closed: {closed}, Currently Open: {currently_open}",
                target_value=40,
                meets_criteria=meets_criteria,
                calculated_by=username,
                notes=f"Opened: {opened}, Closed: {closed}"
            )

            return {
                'opened': opened,
                'closed': closed,
                'currently_open': currently_open,
                'meets_criteria': meets_criteria
            }

        finally:
            self.pool.return_connection(conn)

    def calculate_wo_backlog(self, measurement_period, username=None):
        """
        Calculate WO Backlog
        Formula: Total of WO open
        Target: <10% of the WO raised in a month
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()

            # Parse period
            year, month = map(int, measurement_period.split('-'))
            start_date = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day}"

            # Count WO raised this month (CMs created in this period)
            cursor.execute("""
                SELECT COUNT(*) FROM corrective_maintenance
                WHERE created_date::date >= %s::date AND created_date::date <= %s::date
            """, (start_date, end_date))
            raised_this_month = cursor.fetchone()[0]

            # Count open WO from this month (CMs created in this period that are still Open)
            cursor.execute("""
                SELECT COUNT(*) FROM corrective_maintenance
                WHERE created_date::date >= %s::date AND created_date::date <= %s::date
                AND status = 'Open'
            """, (start_date, end_date))
            open_wo = cursor.fetchone()[0]

            cursor.close()

            # Calculate percentage
            if raised_this_month > 0:
                backlog_pct = (open_wo / raised_this_month) * 100
                meets_criteria = backlog_pct < 10
            else:
                backlog_pct = 0
                meets_criteria = open_wo == 0

            # Save result
            self.save_kpi_result(
                kpi_name='WO Backlog',
                measurement_period=measurement_period,
                calculated_value=open_wo,
                calculated_text=f"{open_wo} open ({backlog_pct:.1f}% of {raised_this_month} raised)",
                target_value=raised_this_month * 0.1 if raised_this_month > 0 else 0,
                meets_criteria=meets_criteria,
                calculated_by=username,
                notes=f"Open: {open_wo}, Raised this month: {raised_this_month}"
            )

            return {
                'open_wo': open_wo,
                'raised_this_month': raised_this_month,
                'backlog_pct': round(backlog_pct, 2),
                'meets_criteria': meets_criteria
            }

        finally:
            self.pool.return_connection(conn)

    def calculate_wo_age_profile(self, measurement_period, username=None):
        """
        Calculate WO age profile
        Formula: Age of work order
        Target: Nb of WO to exceed 60 days
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()

            # Get all open WOs (using status field)
            cursor.execute("""
                SELECT id, created_date
                FROM corrective_maintenance
                WHERE status = 'Open'
            """)
            open_wos = cursor.fetchall()

            cursor.close()

            # Calculate age for each
            now = datetime.now().date()
            over_60_days = 0
            ages = []

            for wo_id, created_date in open_wos:
                if created_date:
                    # Convert created_date to date object if it's not already
                    if isinstance(created_date, str):
                        try:
                            created_date = datetime.strptime(created_date, '%Y-%m-%d').date()
                        except:
                            try:
                                created_date = datetime.strptime(created_date, '%Y-%m-%d %H:%M:%S').date()
                            except:
                                continue
                    elif isinstance(created_date, datetime):
                        created_date = created_date.date()

                    age = (now - created_date).days
                    ages.append(age)
                    if age > 60:
                        over_60_days += 1

            avg_age = sum(ages) / len(ages) if ages else 0
            meets_criteria = over_60_days == 0

            # Save result
            self.save_kpi_result(
                kpi_name='WO age profile',
                measurement_period=measurement_period,
                calculated_value=over_60_days,
                calculated_text=f"{over_60_days} WOs over 60 days old (avg age: {avg_age:.1f} days)",
                target_value=0,
                meets_criteria=meets_criteria,
                calculated_by=username,
                notes=f"Total open WOs: {len(open_wos)}, Average age: {avg_age:.1f} days"
            )

            return {
                'over_60_days': over_60_days,
                'total_open': len(open_wos),
                'avg_age': round(avg_age, 1),
                'meets_criteria': meets_criteria
            }

        finally:
            self.pool.return_connection(conn)

    def calculate_all_auto_kpis(self, measurement_period, username=None):
        """Calculate all KPIs that can be auto-calculated from database"""
        results = {}

        try:
            print(f"Calculating PM Adherence for {measurement_period}...")
            results['pm_adherence'] = self.calculate_pm_adherence(measurement_period, username)
            print("✓ PM Adherence calculated")
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"✗ PM Adherence error: {error_msg}")
            results['pm_adherence'] = {'error': error_msg}

        try:
            print(f"Calculating WO Opened vs Closed for {measurement_period}...")
            results['wo_opened_closed'] = self.calculate_wo_opened_vs_closed(measurement_period, username)
            print("✓ WO Opened vs Closed calculated")
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"✗ WO Opened vs Closed error: {error_msg}")
            results['wo_opened_closed'] = {'error': error_msg}

        try:
            print(f"Calculating WO Backlog for {measurement_period}...")
            results['wo_backlog'] = self.calculate_wo_backlog(measurement_period, username)
            print("✓ WO Backlog calculated")
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"✗ WO Backlog error: {error_msg}")
            results['wo_backlog'] = {'error': error_msg}

        try:
            print(f"Calculating WO Age Profile for {measurement_period}...")
            results['wo_age_profile'] = self.calculate_wo_age_profile(measurement_period, username)
            print("✓ WO Age Profile calculated")
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"✗ WO Age Profile error: {error_msg}")
            results['wo_age_profile'] = {'error': error_msg}

        return results

    def get_kpis_needing_manual_data(self):
        """Get list of all 17 KPIs that require manual data input"""
        return [
            'FR1',
            'Near Miss',
            'TTR (Time to Repair) Adherence',
            'MTBF Mean Time Between Failure',
            'Technical Availability Adherence',
            'MRT (Mean Response Time)',
            'WO opened vs WO closed',
            'WO Backlog',
            'WO age profile',
            'Preventive Maintenance Adherence',
            'Top Breakdown',
            'Purchaser Monthly process Confirmation',
            'Purchaser satisfaction',
            'Non Conformances raised',
            'Non Conformances closed',
            'Mean Time to Deliver a Quote',
            'Purchaser Satisfaction Survey'
        ]

    def get_required_fields_for_kpi(self, kpi_name):
        """Get required manual input fields for a specific KPI"""
        fields = {
            'FR1': [
                {'field': 'accident_count', 'label': 'Number of Accidents (sick leave > 24h)', 'type': 'number'},
                {'field': 'hours_worked', 'label': 'Number of Hours Worked', 'type': 'number'}
            ],
            'Near Miss': [
                {'field': 'near_miss_count', 'label': 'Number of Near Miss Reports', 'type': 'number'}
            ],
            'TTR (Time to Repair) Adherence': [
                {'field': 'p1_within_target', 'label': 'P1 Assets Fixed Within 2 Hours', 'type': 'number'},
                {'field': 'p1_total', 'label': 'Total P1 Asset Failures', 'type': 'number'},
                {'field': 'p2_within_target', 'label': 'P2 Assets Fixed Within 4 Hours', 'type': 'number'},
                {'field': 'p2_total', 'label': 'Total P2 Asset Failures', 'type': 'number'}
            ],
            'MTBF Mean Time Between Failure': [
                {'field': 'p1_operating_hours', 'label': 'P1 Assets Total Operating Hours', 'type': 'number'},
                {'field': 'p1_failure_count', 'label': 'P1 Assets Failure Count', 'type': 'number'},
                {'field': 'p2_operating_hours', 'label': 'P2 Assets Total Operating Hours', 'type': 'number'},
                {'field': 'p2_failure_count', 'label': 'P2 Assets Failure Count', 'type': 'number'}
            ],
            'Technical Availability Adherence': [
                {'field': 'p1_assets_meeting_target', 'label': 'P1 Assets Meeting >95% Availability', 'type': 'number'},
                {'field': 'p1_total_assets', 'label': 'Total P1 Assets', 'type': 'number'}
            ],
            'MRT (Mean Response Time)': [
                {'field': 'total_response_time_minutes', 'label': 'Total Response Time (minutes)', 'type': 'number'},
                {'field': 'wo_count', 'label': 'Number of Work Orders', 'type': 'number'}
            ],
            'WO opened vs WO closed': [
                {'field': 'wo_opened', 'label': 'Number of Work Orders Opened', 'type': 'number'},
                {'field': 'wo_closed', 'label': 'Number of Work Orders Closed', 'type': 'number'},
                {'field': 'wo_currently_open', 'label': 'Number of Work Orders Currently Open', 'type': 'number'}
            ],
            'WO Backlog': [
                {'field': 'wo_raised_this_month', 'label': 'Work Orders Raised This Month', 'type': 'number'},
                {'field': 'wo_open', 'label': 'Work Orders Still Open', 'type': 'number'}
            ],
            'WO age profile': [
                {'field': 'wo_over_60_days', 'label': 'Work Orders Over 60 Days Old', 'type': 'number'},
                {'field': 'total_open_wo', 'label': 'Total Open Work Orders', 'type': 'number'},
                {'field': 'avg_age_days', 'label': 'Average Age of Open WOs (days)', 'type': 'number'}
            ],
            'Preventive Maintenance Adherence': [
                {'field': 'pm_scheduled', 'label': 'PM Work Orders Scheduled', 'type': 'number'},
                {'field': 'pm_completed', 'label': 'PM Work Orders Completed', 'type': 'number'}
            ],
            'Non Conformances raised': [
                {'field': 'nc_count', 'label': 'Number of Non-Conformances Raised', 'type': 'number'}
            ],
            'Non Conformances closed': [
                {'field': 'nc_closed_on_time', 'label': 'Non-Conformances Closed On Time', 'type': 'number'},
                {'field': 'nc_total', 'label': 'Total Non-Conformances Due', 'type': 'number'}
            ],
            'Mean Time to Deliver a Quote': [
                {'field': 'total_quote_time_hours', 'label': 'Total Quote Delivery Time (hours)', 'type': 'number'},
                {'field': 'quote_count', 'label': 'Number of Quotes Requested', 'type': 'number'}
            ],
            'Purchaser satisfaction': [
                {'field': 'satisfaction_score', 'label': 'Satisfaction Score (%)', 'type': 'number'}
            ],
            'Purchaser Satisfaction Survey': [
                {'field': 'survey_score', 'label': 'Yearly Satisfaction Survey Score (%)', 'type': 'number'}
            ],
            'Top Breakdown': [
                {'field': 'breakdown_analysis', 'label': 'Breakdown Analysis (Pareto)', 'type': 'text'}
            ],
            'Purchaser Monthly process Confirmation': [
                {'field': 'confirmation_score', 'label': 'Confirmation Score (%)', 'type': 'number'}
            ]
        }
        return fields.get(kpi_name, [])

    def calculate_manual_kpi(self, kpi_name, measurement_period, username=None):
        """Calculate KPI from manual input data"""
        try:
            print(f"Calculating manual KPI: {kpi_name} for {measurement_period}...")
            manual_data = self.get_manual_data(kpi_name, measurement_period)

            if not manual_data:
                print(f"✗ No manual data found for {kpi_name}")
                return {'error': 'No manual data entered for this period'}

            print(f"Found {len(manual_data)} data fields for {kpi_name}")

            # Convert to dict for easier access
            data_dict = {row['data_field']: row['data_value'] or row['data_text'] for row in manual_data}
            print(f"Data fields: {list(data_dict.keys())}")
            print(f"Data values: {data_dict}")

            result = None
            meets_criteria = None
            calculated_text = None

            # Calculate based on KPI type
            if kpi_name == 'FR1':
                accidents = float(data_dict.get('accident_count') or 0)
                hours = float(data_dict.get('hours_worked') or 1)
                if hours > 0:
                    result = (accidents / hours) * 1_000_000
                    meets_criteria = result == 0
                    calculated_text = f"{accidents} accidents per {hours:,.0f} hours worked"

            elif kpi_name == 'Near Miss':
                result = float(data_dict.get('near_miss_count') or 0)
                calculated_text = f"{int(result)} near miss reports"
                meets_criteria = None  # No specific target

            elif kpi_name == 'TTR (Time to Repair) Adherence':
                p1_within = float(data_dict.get('p1_within_target') or 0)
                p1_total = float(data_dict.get('p1_total') or 0)
                p2_within = float(data_dict.get('p2_within_target') or 0)
                p2_total = float(data_dict.get('p2_total') or 0)

                # Calculate combined adherence for P1 and P2
                total_within = p1_within + p2_within
                total_failures = p1_total + p2_total

                if total_failures > 0:
                    result = (total_within / total_failures) * 100
                    meets_criteria = result >= 95
                    calculated_text = f"P1: {p1_within}/{p1_total}, P2: {p2_within}/{p2_total} within target ({result:.1f}%)"
                else:
                    # No failures means perfect adherence (100%)
                    result = 100.0
                    meets_criteria = True
                    calculated_text = "No P1 or P2 failures - 100% adherence"

            elif kpi_name == 'MTBF Mean Time Between Failure':
                p1_hours = float(data_dict.get('p1_operating_hours') or 0)
                p1_failures = float(data_dict.get('p1_failure_count') or 0)
                if p1_failures > 0:
                    result = p1_hours / p1_failures
                    meets_criteria = result > 80
                    calculated_text = f"{result:.1f} hours between failures (P1 assets)"
                else:
                    # No failures - cannot calculate MTBF
                    result = None
                    meets_criteria = None
                    calculated_text = "No failures recorded - MTBF N/A"

            elif kpi_name == 'Technical Availability Adherence':
                meeting = float(data_dict.get('p1_assets_meeting_target') or 0)
                total = float(data_dict.get('p1_total_assets') or 0)
                if total > 0:
                    result = (meeting / total) * 100
                    meets_criteria = result >= 95
                    calculated_text = f"{meeting}/{total} P1 assets meeting >95% availability"
                else:
                    # No assets to measure
                    result = None
                    meets_criteria = None
                    calculated_text = "No P1 assets to measure - N/A"

            elif kpi_name == 'MRT (Mean Response Time)':
                total_time = float(data_dict.get('total_response_time_minutes') or 0)
                wo_count = float(data_dict.get('wo_count') or 0)
                if wo_count > 0:
                    result = total_time / wo_count
                    meets_criteria = result <= 15  # P1 target
                    calculated_text = f"{result:.1f} minutes average response time"
                else:
                    # No work orders to measure
                    result = None
                    meets_criteria = None
                    calculated_text = "No work orders - MRT N/A"

            elif kpi_name == 'Non Conformances raised':
                result = float(data_dict.get('nc_count') or 0)
                meets_criteria = result == 0
                calculated_text = f"{int(result)} non-conformances raised"

            elif kpi_name == 'Non Conformances closed':
                closed = float(data_dict.get('nc_closed_on_time') or 0)
                total = float(data_dict.get('nc_total') or 0)
                if total > 0:
                    result = (closed / total) * 100
                    meets_criteria = result == 100
                    calculated_text = f"{closed}/{total} closed on time"
                else:
                    # No non-conformances means 100% compliance
                    result = 100.0
                    meets_criteria = True
                    calculated_text = "No non-conformances - 100% compliance"

            elif kpi_name == 'Mean Time to Deliver a Quote':
                total_hours = float(data_dict.get('total_quote_time_hours') or 0)
                quote_count = float(data_dict.get('quote_count') or 0)
                if quote_count > 0:
                    result = total_hours / quote_count
                    meets_criteria = result <= 48
                    calculated_text = f"{result:.1f} hours average delivery time"
                else:
                    # No quotes to measure
                    result = None
                    meets_criteria = None
                    calculated_text = "No quotes delivered - N/A"

            elif kpi_name == 'Purchaser satisfaction':
                result = float(data_dict.get('satisfaction_score') or 0)
                meets_criteria = result >= 90
                calculated_text = f"{result}% satisfaction score"

            elif kpi_name == 'Purchaser Monthly process Confirmation':
                result = float(data_dict.get('confirmation_score') or 0)
                meets_criteria = result >= 90
                calculated_text = f"{result}% confirmation score"

            elif kpi_name == 'Top Breakdown':
                calculated_text = data_dict.get('breakdown_analysis') or 'N/A'
                result = None

            elif kpi_name == 'WO opened vs WO closed':
                opened = float(data_dict.get('wo_opened') or 0)
                closed = float(data_dict.get('wo_closed') or 0)
                currently_open = float(data_dict.get('wo_currently_open') or 0)
                result = currently_open
                meets_criteria = currently_open <= 40
                calculated_text = f"Opened: {int(opened)}, Closed: {int(closed)}, Currently Open: {int(currently_open)}"

            elif kpi_name == 'WO Backlog':
                raised = float(data_dict.get('wo_raised_this_month') or 0)
                open_wo = float(data_dict.get('wo_open') or 0)
                if raised > 0:
                    backlog_pct = (open_wo / raised) * 100
                    result = open_wo
                    meets_criteria = backlog_pct < 10
                    calculated_text = f"{int(open_wo)} open ({backlog_pct:.1f}% of {int(raised)} raised)"
                else:
                    result = open_wo
                    meets_criteria = open_wo == 0
                    calculated_text = f"{int(open_wo)} open (no WOs raised this month)"

            elif kpi_name == 'WO age profile':
                over_60 = float(data_dict.get('wo_over_60_days') or 0)
                total_open = float(data_dict.get('total_open_wo') or 0)
                avg_age = float(data_dict.get('avg_age_days') or 0)
                result = over_60
                meets_criteria = over_60 == 0
                calculated_text = f"{int(over_60)} WOs over 60 days old (avg age: {avg_age:.1f} days)"

            elif kpi_name == 'Preventive Maintenance Adherence':
                scheduled = float(data_dict.get('pm_scheduled') or 0)
                completed = float(data_dict.get('pm_completed') or 0)
                if scheduled > 0:
                    result = (completed / scheduled) * 100
                    meets_criteria = result >= 95
                    calculated_text = f"{int(completed)}/{int(scheduled)} completed ({result:.1f}%)"
                else:
                    result = 0
                    meets_criteria = None
                    calculated_text = "No PM scheduled"

            elif kpi_name == 'Purchaser Satisfaction Survey':
                result = float(data_dict.get('survey_score') or 0)
                meets_criteria = result >= 90
                calculated_text = f"{result}% satisfaction score"

            # Save the result
            if result is not None or calculated_text:
                print(f"Saving KPI result: {kpi_name} = {result or calculated_text}")
                self.save_kpi_result(
                    kpi_name=kpi_name,
                    measurement_period=measurement_period,
                    calculated_value=result,
                    calculated_text=calculated_text,
                    meets_criteria=meets_criteria,
                    calculated_by=username
                )
                print(f"✓ {kpi_name} calculated successfully")

            return {
                'value': result,
                'text': calculated_text,
                'meets_criteria': meets_criteria
            }

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"✗ Error calculating {kpi_name}: {error_msg}")
            return {'error': error_msg}
