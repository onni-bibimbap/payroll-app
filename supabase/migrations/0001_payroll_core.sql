-- 0001_payroll_core.sql — baseline: existing payroll app tables (from app/models.py)
begin;
CREATE TABLE IF NOT EXISTS employees (
	id SERIAL NOT NULL, 
	emp_code VARCHAR(24) NOT NULL, 
	reg_ref VARCHAR(64), 
	name VARCHAR(128) NOT NULL, 
	email VARCHAR(128), 
	phone VARCHAR(48), 
	nric VARCHAR(48), 
	dob DATE, 
	bank_name VARCHAR(64), 
	bank_account VARCHAR(64), 
	position VARCHAR(64), 
	employment_type VARCHAR(16) NOT NULL, 
	basic_salary NUMERIC(12, 2) NOT NULL, 
	hourly_rate NUMERIC(12, 2) NOT NULL, 
	ot_rate NUMERIC(12, 2) NOT NULL, 
	epf_enabled BOOLEAN NOT NULL, 
	socso_enabled BOOLEAN NOT NULL, 
	allowance_eligible BOOLEAN NOT NULL, 
	is_foreign BOOLEAN NOT NULL, 
	active BOOLEAN NOT NULL, 
	inactive_reason VARCHAR(64), 
	needs_review BOOLEAN NOT NULL, 
	import_note TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_employees_emp_code ON employees (emp_code);
CREATE INDEX IF NOT EXISTS ix_employees_name ON employees (name);
CREATE TABLE IF NOT EXISTS payroll_runs (
	id SERIAL NOT NULL, 
	year INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	note TEXT, 
	remarks TEXT, 
	work_days_default INTEGER NOT NULL, 
	prepared_by VARCHAR(64), 
	approved_by VARCHAR(64), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE, 
	approved_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_run_year_month UNIQUE (year, month)
);

CREATE TABLE IF NOT EXISTS settings (
	id INTEGER NOT NULL, 
	company_name VARCHAR(64) NOT NULL, 
	default_work_days INTEGER NOT NULL, 
	default_ot_rate NUMERIC(12, 2) NOT NULL, 
	epf_emp_rate NUMERIC(7, 5) NOT NULL, 
	epf_er_rate_low NUMERIC(7, 5) NOT NULL, 
	epf_er_rate_high NUMERIC(7, 5) NOT NULL, 
	epf_er_threshold NUMERIC(12, 2) NOT NULL, 
	socso_eis_ceiling NUMERIC(12, 2) NOT NULL, 
	socso_c1_emp NUMERIC(7, 5) NOT NULL, 
	socso_c1_er NUMERIC(7, 5) NOT NULL, 
	socso_c2_er NUMERIC(7, 5) NOT NULL, 
	eis_rate NUMERIC(7, 5) NOT NULL, 
	personal_relief NUMERIC(12, 2) NOT NULL, 
	epf_relief_cap NUMERIC(12, 2) NOT NULL, 
	tax_rebate NUMERIC(12, 2) NOT NULL, 
	rebate_ceiling NUMERIC(12, 2) NOT NULL, 
	default_include_allowance BOOLEAN NOT NULL, 
	default_include_ot BOOLEAN NOT NULL, 
	ft_default_epf BOOLEAN NOT NULL, 
	ft_default_socso BOOLEAN NOT NULL, 
	pt_default_epf BOOLEAN NOT NULL, 
	pt_default_socso BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS users (
	id SERIAL NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	full_name VARCHAR(128) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE TABLE IF NOT EXISTS payslips (
	id SERIAL NOT NULL, 
	run_id INTEGER NOT NULL, 
	employee_id INTEGER NOT NULL, 
	emp_code VARCHAR(24) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	bank_name VARCHAR(64), 
	bank_account VARCHAR(64), 
	employment_type VARCHAR(16) NOT NULL, 
	basic NUMERIC(12, 2) NOT NULL, 
	count_by_day BOOLEAN NOT NULL, 
	hourly BOOLEAN NOT NULL, 
	rate NUMERIC(12, 2) NOT NULL, 
	units NUMERIC(8, 2) NOT NULL, 
	allowance_enabled BOOLEAN NOT NULL, 
	allowance NUMERIC(12, 2) NOT NULL, 
	deduction_enabled BOOLEAN NOT NULL, 
	deduction NUMERIC(12, 2) NOT NULL, 
	deduction_reason VARCHAR(160), 
	ot_enabled BOOLEAN NOT NULL, 
	ot_hours NUMERIC(7, 2) NOT NULL, 
	ot_rate NUMERIC(12, 2) NOT NULL, 
	epf_enabled BOOLEAN NOT NULL, 
	socso_enabled BOOLEAN NOT NULL, 
	include_allowance BOOLEAN NOT NULL, 
	include_ot BOOLEAN NOT NULL, 
	over_60 BOOLEAN NOT NULL, 
	"foreign" BOOLEAN NOT NULL, 
	pcb_override NUMERIC(12, 2), 
	notes TEXT, 
	base_earning NUMERIC(12, 2) NOT NULL, 
	allowance_total NUMERIC(12, 2) NOT NULL, 
	gross NUMERIC(12, 2) NOT NULL, 
	statutory_wage NUMERIC(12, 2) NOT NULL, 
	ot_pay NUMERIC(12, 2) NOT NULL, 
	total_remuneration NUMERIC(12, 2) NOT NULL, 
	epf_employee NUMERIC(12, 2) NOT NULL, 
	epf_employer NUMERIC(12, 2) NOT NULL, 
	socso_employee NUMERIC(12, 2) NOT NULL, 
	socso_employer NUMERIC(12, 2) NOT NULL, 
	eis_employee NUMERIC(12, 2) NOT NULL, 
	eis_employer NUMERIC(12, 2) NOT NULL, 
	chargeable_income NUMERIC(12, 2) NOT NULL, 
	pcb NUMERIC(12, 2) NOT NULL, 
	deduction_amount NUMERIC(12, 2) NOT NULL, 
	total_employee_deduction NUMERIC(12, 2) NOT NULL, 
	net_salary NUMERIC(12, 2) NOT NULL, 
	employer_statutory NUMERIC(12, 2) NOT NULL, 
	employer_cost NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES payroll_runs (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id)
);

CREATE INDEX IF NOT EXISTS ix_payslips_run_id ON payslips (run_id);
CREATE INDEX IF NOT EXISTS ix_payslips_employee_id ON payslips (employee_id);
commit;
