CREATE TABLE IF NOT EXISTS OPERATIONAL_POINT (
	OPP_id varchar PRIMARY KEY, 
	OPP_name varchar ,
	OPP_uniqueid varchar UNIQUE,
	OPP_lon float8 ,
	OPP_lat float8 ,
	OPP_geom geometry(POINT,4326),
	OPP_taftapcode varchar,
	OPP_date_start date,
	OPP_date_end date,
	OPP_track_nb integer ,
	OPP_tunnel_nb integer ,
	OPP_platform_nb integer ,
	OTY_id int ,
	MEM_id varchar 
);


CREATE TABLE IF NOT EXISTS SECTION_OF_LINE (
	SOL_id varchar PRIMARY KEY,
	SOL_length float8,
	SOL_nature varchar,
	SOL_imcode varchar,
	SOL_date_start date ,
	SOL_date_end date ,
	SOL_track_nb integer ,
	SOL_tunnel_nb integer ,
	OPP_start varchar REFERENCES OPERATIONAL_POINT(OPP_uniqueid) ON DELETE CASCADE,
	OPP_end varchar REFERENCES OPERATIONAL_POINT(OPP_uniqueid) ON DELETE CASCADE,
	MEM_id varchar ,
	LIN_id varchar ,
	UNIQUE(OPP_start, OPP_end)
);

