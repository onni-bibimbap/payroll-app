--
-- PostgreSQL database dump
--

\restrict xyUirTtTk94ruIIN92vd6uivb6FwbKI8Pdv1pVBZdicI6GRmvzEkVFVs7FixdKE

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: employees; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employees (
    id integer NOT NULL,
    emp_code character varying(24) NOT NULL,
    reg_ref character varying(64),
    name character varying(128) NOT NULL,
    email character varying(128),
    phone character varying(48),
    nric character varying(48),
    dob date,
    bank_name character varying(64),
    bank_account character varying(64),
    "position" character varying(64),
    employment_type character varying(16) NOT NULL,
    basic_salary numeric(12,2) NOT NULL,
    hourly_rate numeric(12,2) NOT NULL,
    ot_rate numeric(12,2) NOT NULL,
    epf_enabled boolean NOT NULL,
    socso_enabled boolean NOT NULL,
    allowance_eligible boolean NOT NULL,
    is_foreign boolean NOT NULL,
    active boolean NOT NULL,
    inactive_reason character varying(64),
    needs_review boolean NOT NULL,
    import_note text,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.employees OWNER TO postgres;

--
-- Name: employees_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.employees_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.employees_id_seq OWNER TO postgres;

--
-- Name: employees_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.employees_id_seq OWNED BY public.employees.id;


--
-- Name: payroll_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payroll_runs (
    id integer NOT NULL,
    year integer NOT NULL,
    month integer NOT NULL,
    status character varying(16) NOT NULL,
    note text,
    remarks text,
    work_days_default integer NOT NULL,
    prepared_by character varying(64),
    approved_by character varying(64),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    submitted_at timestamp without time zone,
    approved_at timestamp without time zone
);


ALTER TABLE public.payroll_runs OWNER TO postgres;

--
-- Name: payroll_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payroll_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payroll_runs_id_seq OWNER TO postgres;

--
-- Name: payroll_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payroll_runs_id_seq OWNED BY public.payroll_runs.id;


--
-- Name: payslips; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payslips (
    id integer NOT NULL,
    run_id integer NOT NULL,
    employee_id integer NOT NULL,
    emp_code character varying(24) NOT NULL,
    name character varying(128) NOT NULL,
    bank_name character varying(64),
    bank_account character varying(64),
    employment_type character varying(16) NOT NULL,
    basic numeric(12,2) NOT NULL,
    count_by_day boolean NOT NULL,
    hourly boolean NOT NULL,
    rate numeric(12,2) NOT NULL,
    units numeric(8,2) NOT NULL,
    allowance_enabled boolean NOT NULL,
    allowance numeric(12,2) NOT NULL,
    deduction_enabled boolean NOT NULL,
    deduction numeric(12,2) NOT NULL,
    deduction_reason character varying(160),
    ot_enabled boolean NOT NULL,
    ot_hours numeric(7,2) NOT NULL,
    ot_rate numeric(12,2) NOT NULL,
    epf_enabled boolean NOT NULL,
    socso_enabled boolean NOT NULL,
    include_allowance boolean NOT NULL,
    include_ot boolean NOT NULL,
    over_60 boolean NOT NULL,
    "foreign" boolean NOT NULL,
    pcb_override numeric(12,2),
    notes text,
    base_earning numeric(12,2) NOT NULL,
    allowance_total numeric(12,2) NOT NULL,
    gross numeric(12,2) NOT NULL,
    statutory_wage numeric(12,2) NOT NULL,
    ot_pay numeric(12,2) NOT NULL,
    total_remuneration numeric(12,2) NOT NULL,
    epf_employee numeric(12,2) NOT NULL,
    epf_employer numeric(12,2) NOT NULL,
    socso_employee numeric(12,2) NOT NULL,
    socso_employer numeric(12,2) NOT NULL,
    eis_employee numeric(12,2) NOT NULL,
    eis_employer numeric(12,2) NOT NULL,
    chargeable_income numeric(12,2) NOT NULL,
    pcb numeric(12,2) NOT NULL,
    deduction_amount numeric(12,2) NOT NULL,
    total_employee_deduction numeric(12,2) NOT NULL,
    net_salary numeric(12,2) NOT NULL,
    employer_statutory numeric(12,2) NOT NULL,
    employer_cost numeric(12,2) NOT NULL
);


ALTER TABLE public.payslips OWNER TO postgres;

--
-- Name: payslips_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payslips_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payslips_id_seq OWNER TO postgres;

--
-- Name: payslips_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payslips_id_seq OWNED BY public.payslips.id;


--
-- Name: settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.settings (
    id integer NOT NULL,
    company_name character varying(64) NOT NULL,
    default_work_days integer NOT NULL,
    default_ot_rate numeric(12,2) NOT NULL,
    epf_emp_rate numeric(7,5) NOT NULL,
    epf_er_rate_low numeric(7,5) NOT NULL,
    epf_er_rate_high numeric(7,5) NOT NULL,
    epf_er_threshold numeric(12,2) NOT NULL,
    socso_eis_ceiling numeric(12,2) NOT NULL,
    socso_c1_emp numeric(7,5) NOT NULL,
    socso_c1_er numeric(7,5) NOT NULL,
    socso_c2_er numeric(7,5) NOT NULL,
    eis_rate numeric(7,5) NOT NULL,
    personal_relief numeric(12,2) NOT NULL,
    epf_relief_cap numeric(12,2) NOT NULL,
    tax_rebate numeric(12,2) NOT NULL,
    rebate_ceiling numeric(12,2) NOT NULL,
    default_include_allowance boolean NOT NULL,
    default_include_ot boolean NOT NULL,
    ft_default_epf boolean NOT NULL,
    ft_default_socso boolean NOT NULL,
    pt_default_epf boolean NOT NULL,
    pt_default_socso boolean NOT NULL
);


ALTER TABLE public.settings OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(64) NOT NULL,
    full_name character varying(128) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: employees id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees ALTER COLUMN id SET DEFAULT nextval('public.employees_id_seq'::regclass);


--
-- Name: payroll_runs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_runs ALTER COLUMN id SET DEFAULT nextval('public.payroll_runs_id_seq'::regclass);


--
-- Name: payslips id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payslips ALTER COLUMN id SET DEFAULT nextval('public.payslips_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: employees; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employees (id, emp_code, reg_ref, name, email, phone, nric, dob, bank_name, bank_account, "position", employment_type, basic_salary, hourly_rate, ot_rate, epf_enabled, socso_enabled, allowance_eligible, is_foreign, active, inactive_reason, needs_review, import_note, created_at) FROM stdin;
1	ONNI0001	001	cheong hoong jun	junnyea@hotmail.com	017-3903885	890310	2025-03-04	alliance	13213213	manager	full_time	2000.00	0.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "2000.0"; DOB gives an unusual age — confirm	2026-07-01 13:39:15
2	ONNI0002	9822	POH ZHI QING	qqing0818@gmail.com	0169802263	070818141138	2007-08-18	Maybank	1648 1030 4828	Waiter / Waitress	full_time	1800.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "1800.0"	2026-07-01 13:39:15
3	ONNI0003	6625	low guan hong	softbread999@gmail.com	0166510068	900305146347	1990-03-05	Maybank	114067283679	Chef	full_time	3000.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "3000.0"	2026-07-01 13:39:15
4	ONNI0004	6117	Jackson Tan	mgsmobile12233@gmail.com	01128648851	060214011261	2006-02-14	Pubilc bank	4952447533	Waiter / Waitress	part_time	0.00	9.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "9+ per hour"	2026-07-01 13:39:15
5	ONNI0005	6206	Cheong Fong Cheng	cfc1033@hotmail.com	0122831033	730815015989	1973-08-15	CIMB	7000986177	manager	full_time	5000.00	0.00	0.00	t	t	f	f	t	\N	f	Expected salary text: "5000.0"	2026-07-01 13:39:15
6	ONNI0006	9903	Nor Azaharina Binti Azahar	norazaharina@icloud.com	0162455219	060510031072	2006-05-10	Bank Muamalat	3060010250728	Waiter / Waitress	full_time	2400.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "basic 2400"	2026-07-01 13:39:15
7	ONNI0007	2474	TAN KIAN HOE	alextan8995@gmail.com	0176811969	020620-04-0045	2002-06-20	PUBLIC BANK	6940408214	Waiter / Waitress	full_time	2400.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "2400.0"	2026-07-01 13:39:15
8	ONNI0008	2806	Lee Wen Pang	eason34377@gmail.com	010-6659579	030209010347	2003-02-09	cimb bank	7075999585	Waiter / Waitress	part_time	0.00	9.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "9/above"	2026-07-01 13:39:15
9	ONNI0009	2768	Chow Xin Yi	xinyichow16@gmail.com	0182179147	030805-08-0798	2003-08-05	Maybank	564810579836	Waiter / Waitress	full_time	0.00	0.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "-"; could not read a monthly salary — set it manually	2026-07-01 13:39:15
10	ONNI0010	5033	Tan Yun Ni	tanyunni.290345@gmail.com	012-702 0417	070705140438	2007-07-05	Bank of China	100000400303156	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM8 per hour"	2026-07-01 13:39:15
11	ONNI0011	Onni bibimbap	Chuah hui tian	huitianchuah269@gmail.com	0165260787	020923020738	2002-09-23	Gx bank	03150336298	Chef	full_time	3500.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "3500.0"	2026-07-01 13:39:15
12	ONNI0012	1088	Chen Mei Yee	meiyeec2004@gmail.com	0163238328	040419060288	2004-04-19	Public Bank	5091343401	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "8.0"	2026-07-01 13:39:15
13	ONNI0013	3655	Chin ching hua	qinqinghua4@gmail.com	01111985546	040302081421	2004-03-02	Public bank	5016571402	Chef	full_time	2000.00	0.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "2000-2500"; range given (2000/2500) — took lowest	2026-07-01 13:39:15
14	ONNI0014	\N	Tan Wei Yuan	tanweiyuan999@gmail.com	0148989739	990910145037	1999-09-10	Tan Wei Yuan	564061505594	Waiter / Waitress	full_time	2200.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "2200.0"	2026-07-01 13:39:15
15	ONNI0015	5186	CHIN JIA HUI	cjiahui437@gmail.com	01135538628	031109010790	2003-11-09	CHIN JIA HUI	PUBLIC BANK 4922328724	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "8.0"	2026-07-01 13:39:15
16	ONNI0016	\N	Mohd aminludin bin yahya	aminyahya733@gmail.com	0179102507	040104030607	2004-01-04	MAYBANK	0129 9607 6614	Chef	full_time	2400.00	0.00	0.00	f	t	f	f	t	\N	f	Expected salary text: "2400.0"	2026-07-01 13:39:15
17	ONNI0017	\N	nur alya adriana binti ahmad	alyaadriana640@gmail.com	01129430238	030606030368	2003-06-06	mybank2u	5645 9331 8369	Waiter / Waitress	full_time	2100.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "2100.0"	2026-07-01 13:39:15
18	ONNI0018	\N	刘立仁	vinsonliu7309@gmail.com	0187677309	070909011283	2007-09-09	4576935026	PUBLIC	Waiter / Waitress	full_time	2300.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "2300.0"	2026-07-01 13:39:15
19	ONNI0019	\N	Waynee Woo Min Hui	wayneewoomh@gmail.com	013-3930897	070727-14-0332	2007-07-27	CIMB	7655088359	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "Rm8/hour (part time)/ rm1800+ (full time)"	2026-07-01 13:39:15
20	ONNI0020	3088	Yap Shinny	yapshinny@gmail.com	0173816443	040102140132	2004-01-02	Ambank	8881060899630	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "rm8/per hour"	2026-07-01 13:39:15
21	ONNI0021	6602	Mohd Hafizal bin azahar	aswaniewanie62@gmail.com	0177438854	951107115339	2025-04-16	Public bank	4798247316	Chef	full_time	3000.00	0.00	0.00	f	t	f	f	t	\N	t	Expected salary text: "3000.0"; DOB gives an unusual age — confirm	2026-07-01 13:39:15
22	ONNI0022	4633	Mohammad shah putra danial	diyanafalisya5331@gmail.com	01127097699	830405-12-5331	1983-04-05	Maybank	112205095227	Chef	full_time	3500.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "3500.0"	2026-07-01 13:39:15
23	ONNI0023	2645	Chiam Xue Mei	micolechiam@gmail.com	011 55866511	020220070288	2002-02-20	Maybank	5023 05 7911	Waiter / Waitress	part_time	0.00	10.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM 10 per hour"	2026-07-01 13:39:15
24	ONNI0024	8705	Lim Pei Yu	limpeiyu4@gmail.com	182999098	41101050156	2004-11-01	Maybank	155171337088	Waiter / Waitress	full_time	2500.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "2500.0"	2026-07-01 13:39:15
25	ONNI0025	-	Nicholas Lim Zhuo Heng	nicholaslim1108@gmail.com	012-3019299	071126141289	2025-04-22	Public bank	5032019500	Waiter / Waitress	full_time	2000.00	0.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "2000.0"; DOB gives an unusual age — confirm	2026-07-01 13:39:15
26	ONNI0026	-	Ooi Chien Yun	janicecy07@gmail.com	0124148133	071228140906	2007-12-28	Public Bank	5101050234	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM 8"	2026-07-01 13:39:15
27	ONNI0027	\N	Russell Karl	russellkarl74@gmail.com	0168335466	740906075353	1974-09-06	Public Bank	4887327815	Outlet Manager	full_time	4800.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "4800+"	2026-07-01 13:39:15
28	ONNI0028	9974	ONG WEI SHENG	ongwelson@gmail.com	017-6033429	991211-01-5721	1999-12-11	CIMB	7070746870	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM 8 per hour"	2026-07-01 13:39:15
29	ONNI0029	\N	Mohamad aiman amirul bin azahar	aimanamirulazahar35@gmail.com	0192123361	000707030407	2000-07-07	Maybank	1642 7670 2795	Kitchen helper	full_time	2500.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "2500.0"	2026-07-01 13:39:15
30	ONNI0030	4853	Low Xin Yuan	shinvv14@gmail.com	0186224853	070321140789	2007-03-21	Public Bank	5076043634	Waiter / Waitress	full_time	1800.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM 1,800"	2026-07-01 13:39:15
31	ONNI0031	6989	Derrick Yip Hong Ye	yapy889@gmail.com	01136205880	060729010727	2006-07-29	PbeBank	5082383123 DERRICK YIP HONG YE	Waiter / Waitress	part_time	0.00	10.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM10 per hour"	2026-07-01 13:39:15
32	ONNI0032	1248	NURBAITI	mutyatiarachaniago@gmail.com	01121711248	C9146269	2002-10-13	Mybank	5640 6151 4414	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "2.0"; hourly rate defaulted to RM8 — confirm	2026-07-01 13:39:15
33	ONNI0033	6846	Nicole Wong Yu Xuan	nicolewong324@gmail.com	010-6636846	040311-01-1548	2004-03-11	Nicole Wong Yu Xuan	5089107903 (Public Bank)	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM8 / hour"	2026-07-01 13:39:15
34	ONNI0034	0176029048	TAN KUI THEAN	KyleTan95@gmail.com	0176029048	901001145913	1990-10-01	Maybank	164061854800	Supervisor	full_time	3000.00	0.00	0.00	t	t	f	f	t	\N	f	Expected salary text: "3k++"	2026-07-01 13:39:15
35	ONNI0035	8665	Hou Ching	jhe75482@gmail.com	0192728665	070605140051	2007-06-05	Public Bank	5102691912	Waiter / Waitress	full_time	1800.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "1800.0"	2026-07-01 13:39:15
36	ONNI0036	3874	Ng Moon Shin	030801moon@gmail.com	0182943874	030108100546	2003-01-08	Public bank	6452764927	Waiter / Waitress	full_time	1800.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM1800 (fulltime)"	2026-07-01 13:39:15
37	ONNI0037	2680	Aron Chong Erng	aronchong64@gmail.com	178332680	70928121277	2025-12-11	Cimb bank	7657001861	Waiter / Waitress	full_time	1900.00	0.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "1900-2000"; range given (1900/2000) — took lowest; DOB gives an unusual age — confirm	2026-07-01 13:39:15
38	ONNI0038	Gan Ming Fong	Gan Ming Fong	ganmingfong@gmail.com	0172048982	071114-14-0895	2007-11-14	GAN MING FONG	5115080606	Chef	full_time	1100.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "1100.0"	2026-07-01 13:39:15
39	ONNI0039	0894	Guravneet Singh Gill A/L Gurmit Singh	guravspec8@gmail.com	0149690894	081106140739	2008-11-06	-	-	Part time	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "RM1800"; hourly rate defaulted to RM8 — confirm	2026-07-01 13:39:15
40	ONNI0040	9811	Chan Gi No	gino.rallyart@gmail.com	0162489811	060905040117	2006-09-05	Gino Chan	5102539403	Waiter / Waitress, Kitchen helper	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "8/hr - 10/hr"	2026-07-01 13:39:15
41	ONNI0041	8102	Maahnav A/L Siva Kumar	sivakumarmaahnav@gmail.com	0183768102	081217080505	2008-12-17	Maybank2U	114067182873	Kitchen crew	full_time	1800.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "1800.0"	2026-07-01 13:39:15
42	ONNI0042	1157	TAI JUN XI	junxitai5@gmail.com	0199081157	090426-14-0433	2026-05-02	-	-	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	t	\N	t	Expected salary text: "RM8 per hour"; DOB gives an unusual age — confirm	2026-07-01 13:39:15
43	ONNI0043	9262	CHIN WEI KIT	ck.kit2003@gmail.com	01121929262	030505100021	2003-05-05	Maybank	156244210774	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM8 per hour"	2026-07-01 13:39:15
44	ONNI0044	7380	ONG PEIR ANN	jsyjsy3284@gmail.com	0167060837	070717-01-0729	2007-07-17	PUBLIC BANK	5097798113	Waiter / Waitress	full_time	3700.00	0.00	0.00	f	t	f	f	t	\N	f	Expected salary text: "3700.0"	2026-07-01 13:39:15
45	ONNI0045	1854	Lee young suu	leeyoungsuuleao@gmail.com	60179401854	RM02V03-24-4	2005-01-01	Merchantrade money	4080020107020730	Waiter / Waitress	full_time	2200.00	0.00	0.00	f	t	f	t	f	resigned	f	Expected salary text: "2200.0"	2026-07-01 13:39:15
46	ONNI0046	1107	Soh Jia Man	wynter0278@gmail.com	01136071107	041107010278	2004-11-07	Public Bank	5089470408	Waiter / Waitress	part_time	0.00	10.00	0.00	f	t	f	f	t	\N	f	Expected salary text: "RM10/per hours"	2026-07-01 13:39:15
47	ONNI0047	8595	Thulasi raj Murugan	thulasirajstudy@gmail.com	01131678595	050322101513	2005-03-22	Cimb bank	7651498174	Waiter / Waitress	full_time	800.00	0.00	0.00	f	t	f	f	t	\N	t	Expected salary text: "800.0"; unusually low basic — confirm	2026-07-01 13:39:15
48	ONNI0048	9156	PYAE PHYO LIN	payemyanmar92@gmail.com	01128949156	MI992757	2001-09-13	Merchantrade Money	4080020101161894	Chef	full_time	2000.00	0.00	0.00	f	t	f	t	f	resigned	f	Expected salary text: "2000.0"	2026-07-01 13:39:15
49	ONNI0049	4155	Chen prng ling	pengling122@gmail.com	0177104155	040118-01-1538	2004-01-18	Chen peng ling	5047776827	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "1 hour 8 ringgit"	2026-07-01 13:39:15
50	ONNI0050	9482	Martha	marthasan2005@gmail.com	01131709482	MJ174523	2005-07-29	Cing Sian San	01131709482	Chef, Waiter / Waitress	full_time	1800.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "1800.0"	2026-07-01 13:39:15
51	ONNI0051	354-25-6216975	Bi Le Chhi	bielychhi1@gmail.com	60183822178	UNHCR	2004-02-17	Touch N G	110260489954	Chef	full_time	2100.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "2100RM"	2026-07-01 13:39:15
52	ONNI0052	-	DANISH HARITH BIN MOHD SUKERI	harithdanish566@gmail.com	011-63972132	040308010667	2004-03-08	CIMB	7641087574	Kitchen Helper	full_time	2200.00	0.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "RM2200"	2026-07-01 13:39:15
53	ONNI0053	8227	Liew Chen Hao	liewbenjamin7@gmail.com	+601113358227	070807-14-0797	2007-08-07	Cimb	7659195560	Part time	part_time	0.00	8.00	0.00	f	t	f	f	t	\N	f	Expected salary text: "RM 8/hour"	2026-07-01 13:39:15
54	ONNI0054	8770	Nay Lin zaw	naylinzaw913@gmail.com	01139558770	MI464565	2000-09-23	Merchantrade	500001618970	Chef	full_time	2500.00	0.00	0.00	f	t	f	t	t	\N	f	Expected salary text: "2500.0"	2026-07-01 13:39:15
55	ONNI0055	5920	Shannen Gomes	shannengomes2001@gmail.com	0179825920	010127140254	2001-01-27	Maybank	1642 2167 1954	Waiter / Waitress	full_time	1200.00	0.00	0.00	f	t	f	f	t	\N	f	Expected salary text: "1200.0"	2026-07-01 13:39:15
56	ONNI0056	1269	Soh Jin Xian	jinxiansoh1022@gmail.com	011-64241269	051022-14-1307	2005-10-22	Public Bank	5042846634	Waiter / Waitress	part_time	0.00	10.00	0.00	f	t	f	f	f	resigned	f	Expected salary text: "10/hour"	2026-07-01 13:39:15
57	ONNI0057	2336	CHEE WEI HONG	weihongxie315@gmail.com	0106642336	080410060683	2008-04-10	Maybank	156094626580	Waiter / Waitress	part_time	0.00	8.00	0.00	f	t	f	f	t	\N	f	Expected salary text: "per hour rm8"	2026-07-01 13:39:15
58	ONNI0058	\N	Mohamad hakim hakimi	Muhakimkc670@gmail.con	0178749502	Malay	2026-07-02	CIMB BANK	7625991780	Chef	full_time	2200.00	0.00	0.00	f	t	f	f	f	resigned	t	Expected salary text: "rm2200"; DOB is in the future — likely a data-entry error, confirm	2026-07-01 13:39:15
\.


--
-- Data for Name: payroll_runs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payroll_runs (id, year, month, status, note, remarks, work_days_default, prepared_by, approved_by, created_at, submitted_at, approved_at) FROM stdin;
\.


--
-- Data for Name: payslips; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payslips (id, run_id, employee_id, emp_code, name, bank_name, bank_account, employment_type, basic, count_by_day, hourly, rate, units, allowance_enabled, allowance, deduction_enabled, deduction, deduction_reason, ot_enabled, ot_hours, ot_rate, epf_enabled, socso_enabled, include_allowance, include_ot, over_60, "foreign", pcb_override, notes, base_earning, allowance_total, gross, statutory_wage, ot_pay, total_remuneration, epf_employee, epf_employer, socso_employee, socso_employer, eis_employee, eis_employer, chargeable_income, pcb, deduction_amount, total_employee_deduction, net_salary, employer_statutory, employer_cost) FROM stdin;
\.


--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.settings (id, company_name, default_work_days, default_ot_rate, epf_emp_rate, epf_er_rate_low, epf_er_rate_high, epf_er_threshold, socso_eis_ceiling, socso_c1_emp, socso_c1_er, socso_c2_er, eis_rate, personal_relief, epf_relief_cap, tax_rebate, rebate_ceiling, default_include_allowance, default_include_ot, ft_default_epf, ft_default_socso, pt_default_epf, pt_default_socso) FROM stdin;
1	Onni	26	15.00	0.11000	0.13000	0.12000	5000.00	6000.00	0.00500	0.01750	0.01250	0.00200	9000.00	4000.00	400.00	35000.00	f	f	f	t	f	f
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, full_name, password_hash, role, created_at) FROM stdin;
1	preparer	Payroll Preparer	pbkdf2_sha256$200000$a358e3cde9dfbb297f78de1d19b3e369$3f3f05e97489702c3ca395025e37f54fe6b50abc88d927c1f1ab20f7cacf62d0	preparer	2026-07-01 13:39:15
2	approver	Payroll Approver	pbkdf2_sha256$200000$2cf1f1bb953ced94d74dd06e26c0d591$ba9f5aac2c90b16f6f25a8f900ea550490765e7b7db584051791367d56ef20d5	approver	2026-07-01 13:39:15
3	admin	Administrator	pbkdf2_sha256$200000$470c65e9193228b37c8f0b0ef290c4c7$50ff416bdafde0d687a5c9b220411ed69cbb5587ff966ef6c32d4666c84377bd	admin	2026-07-01 13:39:15
\.


--
-- Name: employees_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.employees_id_seq', 58, true);


--
-- Name: payroll_runs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payroll_runs_id_seq', 1, true);


--
-- Name: payslips_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payslips_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- Name: employees employees_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (id);


--
-- Name: payroll_runs payroll_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_runs
    ADD CONSTRAINT payroll_runs_pkey PRIMARY KEY (id);


--
-- Name: payslips payslips_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payslips
    ADD CONSTRAINT payslips_pkey PRIMARY KEY (id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (id);


--
-- Name: payroll_runs uq_run_year_month; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_runs
    ADD CONSTRAINT uq_run_year_month UNIQUE (year, month);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_employees_emp_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_employees_emp_code ON public.employees USING btree (emp_code);


--
-- Name: ix_employees_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_employees_name ON public.employees USING btree (name);


--
-- Name: ix_payslips_employee_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payslips_employee_id ON public.payslips USING btree (employee_id);


--
-- Name: ix_payslips_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payslips_run_id ON public.payslips USING btree (run_id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: payslips payslips_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payslips
    ADD CONSTRAINT payslips_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id);


--
-- Name: payslips payslips_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payslips
    ADD CONSTRAINT payslips_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.payroll_runs(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;


--
-- Name: TABLE employees; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.employees TO anon;
GRANT ALL ON TABLE public.employees TO authenticated;
GRANT ALL ON TABLE public.employees TO service_role;


--
-- Name: SEQUENCE employees_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.employees_id_seq TO anon;
GRANT ALL ON SEQUENCE public.employees_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.employees_id_seq TO service_role;


--
-- Name: TABLE payroll_runs; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.payroll_runs TO anon;
GRANT ALL ON TABLE public.payroll_runs TO authenticated;
GRANT ALL ON TABLE public.payroll_runs TO service_role;


--
-- Name: SEQUENCE payroll_runs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.payroll_runs_id_seq TO anon;
GRANT ALL ON SEQUENCE public.payroll_runs_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.payroll_runs_id_seq TO service_role;


--
-- Name: TABLE payslips; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.payslips TO anon;
GRANT ALL ON TABLE public.payslips TO authenticated;
GRANT ALL ON TABLE public.payslips TO service_role;


--
-- Name: SEQUENCE payslips_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.payslips_id_seq TO anon;
GRANT ALL ON SEQUENCE public.payslips_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.payslips_id_seq TO service_role;


--
-- Name: TABLE settings; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.settings TO anon;
GRANT ALL ON TABLE public.settings TO authenticated;
GRANT ALL ON TABLE public.settings TO service_role;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.users TO anon;
GRANT ALL ON TABLE public.users TO authenticated;
GRANT ALL ON TABLE public.users TO service_role;


--
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.users_id_seq TO anon;
GRANT ALL ON SEQUENCE public.users_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.users_id_seq TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- PostgreSQL database dump complete
--

\unrestrict xyUirTtTk94ruIIN92vd6uivb6FwbKI8Pdv1pVBZdicI6GRmvzEkVFVs7FixdKE

