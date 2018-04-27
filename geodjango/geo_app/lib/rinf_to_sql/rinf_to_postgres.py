import os
from collections import namedtuple
import argparse
from lxml import etree
import uuid
import pprint
from collections import defaultdict
import json
import re
import psycopg2
from shapely.geometry import Point
from shapely import wkb

# PARAMETER LIST FOR READING FROM RINF XML FILE
WANTED_PARAMETERS = (
    'IPP_LineCat',
    'IPP_TempRange',
    'ILL_GradProfile',
    'IPP_FreightCorridor',
    'IPP_TENClass',
    'ILL_InteropGuage',
    'ILL_MultiNatGuage',
    'ILL_NatGuage',
    'ILL_ProfileNumSwapBodies',
    'ILL_ProfileSemiTrailers',
    'ITP_NomGuage',
    'ITP_CantDeficiency',
    'ITP_RailInclination',
    'ITP_Ballast',
    'ISC_SwitchCrossing',
    'IHR_LevelCrossing',
    'ECS_SystemType',
    'ECS_VolFreq',
    'ECS_MaxTrainCurrent',
    'ECS_RegenerativeBraking',
    'EPA_TSIHeads',
    'EPA_OtherHeads',
    'EPA_StripMaterial',
    'CPE_Level',
    'CPE_Baseline',
    'CPO_Installed',
    'CTD_Detection',
    'IPP_MaxSpeed',
    'ITU_EmergencyPlan',
    'ITU_FireCatReq',
    'ITU_NatFireCatReq',
    'IPL_TENClass',
    'IPL_AssistanceStartingTrain',
    'IPP_MaxSpeed',
    'IPP_MaxAltitude',
    'ECS_MaxWireHeight',
    'CTD_MaxBrakeDist',
    'ILL_MinRadHorzCurve',
    'ECS_MinWireHeight',
    'CTD_MinRimWidth',
    'CTD_MinWheelDiameter',
    'CTD_MinFlangeThickness',
    'CTD_MinFlangeHeight',
    'CTD_MinAxleLoad'   
)


# SQL TEMPLATES
MS_SQL_TEMPLATE = "INSERT INTO MEMBER (MEM_id, MEM_version, DOC_id_id) VALUES (%s,%s,%s);"
LINE_SQL_TEMPLATE = "INSERT INTO LINE (LIN_id, LIN_name, MEM_id) VALUES(%s,%s,%s);"
OP_TYPE_SQL_TEMPLATE = "INSERT INTO OP_TYPE (OTY_id, OTY_name) SELECT %s,%s WHERE NOT exists (SELECT 1 FROM OP_TYPE WHERE OTY_id = %s);"
OP_SQL_TEMPLATE = "INSERT INTO OPERATIONAL_POINT (OPP_id, OPP_name, OPP_uniqueid, OPP_lon, OPP_lat, geom, OPP_taftapcode, OPP_date_start, OPP_date_end, OPP_track_nb, OPP_tunnel_nb, OPP_platform_nb, OTY_id_id, MEM_id_id) VALUES (%s, %s, %s, %s, %s, ST_SetSRID(%s::geometry, 4326), %s, %s, %s, %s, %s, %s, %s, %s);"
SOL_SQL_TEMPLATE = "INSERT INTO SECTION_OF_LINE (SOL_id, SOL_length, SOL_nature, SOL_imcode, SOL_date_start, SOL_date_end, SOL_track_nb, SOL_tunnel_nb, OPP_start, OPP_end, MEM_id, LIN_id ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,(select LIN_id from LINE where LIN_name = %s));"
PARAMETER_SQL_TEMPLATE = "INSERT INTO PARAMETER (PAR_id,PAR_name,PAR_type) SELECT %s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM PARAMETER where PAR_name = %s);"
PARAMETER_DEFINITION_SQL_TEMPLATE = "INSERT INTO PARAMETER_DEFINITION (PAR_name, PPV_value, PPV_optional_value, PAR_id) SELECT %s,%s,%s,(select PAR_id from PARAMETER where PAR_name = %s) WHERE NOT exists (SELECT 1 FROM PARAMETER_DEFINITION WHERE PAR_name = %s AND  PPV_value = %s);"
SOL_PARAMETER_VALUE_SQL_TEMPLATE = "INSERT INTO SOL_PARAMETER_VALUE (SOL_id, PAR_name_id, SPV_value) VALUES (%s,(select PAR_id from PARAMETER where PAR_name = %s),%s);"
OPP_PARAMETER_VALUE_SQL_TEMPLATE = "INSERT INTO OPP_PARAMETER_VALUE (OPV_value, OPP_id_id, PAR_name_id) VALUES (%s,%s,(select PAR_id from PARAMETER where PAR_name = %s));"


RINFExtractorConfig = namedtuple(
    'RINFExtractorConfig', [
        'postgres_host',
        'postgres_port',
        'postgres_user',
        'postgres_password',
        'postgres_db'
    ]
)


class RINFExtractor:
    def __init__(self, config):
        self.__total_rows = 0
        self.__total_integrity_errors = 0
        try:
            conn_string = "host='{}' port = '{}' user='{}' password='{}' dbname='{}'".format(
                config.postgres_host,
                config.postgres_port,
                config.postgres_user,
                config.postgres_password,
                config.postgres_db
            )
            self.__postgres_connection = psycopg2.connect(conn_string)
            self.__postgres_cursor = self.__postgres_connection.cursor()
        except (Exception, psycopg2.DatabaseError) as error:
            raise Exception(
                "RINFExtractor: could not connect to database: %s" % error)

    def test_query(self):
        self.__postgres_cursor.execute("SELECT COUNT(*) FROM line")
        return self.__postgres_cursor.fetchone()

    def close(self):
        self.__postgres_connection.close()

    def parse_xml(self, xml_path):
        self.__MEM_id = None
        self.__postgres_cursor.execute("BEGIN")
        context = etree.iterparse(xml_path)
        ms_extracts = []
        sol_extracts = []
        op_extracts = []
        for event, elem in context:
            if elem.tag == 'MemberStateCode':
                if event == 'end':
                    ms_extracts.append(self.__extract_ms(elem))
                    elem.clear()
            elif elem.tag == 'SectionOfLine':
                if event == 'end':
                    sol_extracts.append(self.__extract_sol(elem))
                    elem.clear()
            elif elem.tag == 'OperationalPoint':
                if event == 'end':
                    op_extracts.append(self.__extract_op(elem))
                    elem.clear()
        del context

        for ms in ms_extracts:
            self.__insert_ms(ms)
        for op in op_extracts:
            self.__insert_op(op)
        for sol in sol_extracts:
            self.__insert_sol(sol)

        self.__postgres_cursor.execute("COMMIT")
        print('total rows:', self.__total_rows)
        print('total integrity errors:', self.__total_integrity_errors)
        self.__total_rows = 0
        self.__total_integrity_errors = 0

    def __insert_ms(self, ms_extract):
        self.__insert(
            MS_SQL_TEMPLATE, ms_extract)

    def __extract_ms(self, ms):
        MEM_id = ms.get("Code")
        DOC_id_id = None
        MEM_version = ms.get("Version")
        self.MEM_id = MEM_id
        return (MEM_id, MEM_version, DOC_id_id)
    
    def __insert_sol(self, sol_extract):
        self.__insert(LINE_SQL_TEMPLATE, sol_extract['line'])
        self.__insert(SOL_SQL_TEMPLATE, sol_extract['sol'])
        for p in sol_extract['parameters']:
            self.__insert(PARAMETER_SQL_TEMPLATE, p)
        for pd in sol_extract['parameter_definitions']:
            self.__insert(
                PARAMETER_DEFINITION_SQL_TEMPLATE, pd)
        for sol_value in sol_extract['parameter_values']:
            self.__insert(
                SOL_PARAMETER_VALUE_SQL_TEMPLATE, sol_value)

    def __extract_sol(self, sol):
        parameter_definitions = []
        parameters = []
        sol_values = []
        LIN_id = str(uuid.uuid4())
        LIN_name = sol.find("SOLLineIdentification").get("Value")
        # SECTION OF LINE
        SOL_id = str(uuid.uuid4())
        SOL_imcode = sol.find("SOLIMCode").get("Value")
        SOL_length = sol.find("SOLLength").get("Value").replace(",", ".")
        SOL_nature = sol.find("SOLNature").get("OptionalValue")
        OPP_start = sol.find("SOLOPStart").get("Value")
        OPP_end = sol.find("SOLOPEnd").get("Value")
        LIN_name = sol.find("SOLLineIdentification").get("Value")
        SOL_date_start = sol.get("ValidityDateStart")
        SOL_date_end = sol.get("ValidityDateEnd")
        SOL_track_nb = 0
        SOL_tunnel_nb = 0
        sol_parameter_list = []
        soltracks = sol.findall('SOLTrack')
        sol_parameters_dict = defaultdict(set)
        for soltrack in soltracks:
            SOL_track_nb += 1
            sol_parameters = soltrack.findall('SOLTrackParameter')
            for sol_parameter in sol_parameters:
                PAR_id = str(uuid.uuid4())
                sol_parameter_id = sol_parameter.get("ID")
                isapplicable = sol_parameter.get("IsApplicable")
                if isapplicable == 'Y' and sol_parameter_id in WANTED_PARAMETERS:
                    PAR_value = sol_parameter.get("Value")
                    PPV_optional_value = sol_parameter.get("OptionalValue")
                    sol_parameter_list.append((sol_parameter_id, PAR_value))
                    PAR_type = 'SOL_TRACK'
                    parameters.append(
                        (PAR_id, sol_parameter_id, PAR_type, sol_parameter_id,))
                    if PPV_optional_value != None:
                        parameter_definitions.append(
                            (sol_parameter_id, PAR_value, PPV_optional_value, PAR_id, sol_parameter_id, PAR_value))
            for key, value in sol_parameter_list:
                if value != sol_parameters_dict[key]:
                    sol_parameters_dict[key].add(value)
        # COUNT SOL_TUNNEL
            soltunnels = soltrack.findall('SOLTunnel')
            for soltunnel in soltunnels:
                SOL_tunnel_nb += 1
                soltunnel_parameters = soltunnel.findall('SOLTunnelParameter')
                for soltunnel_parameter in soltunnel_parameters:
                    sol_parameter_id = soltunnel_parameter.get("ID")
                    isapplicable = soltunnel_parameter.get("IsApplicable")
                    if isapplicable == 'Y' and sol_parameter_id in WANTED_PARAMETERS:
                        PAR_value = int(soltunnel_parameter.get("Value"))
                        PPV_optional_value = soltunnel_parameter.get(
                            "OptionalValue")
                        sol_parameter_list.append(
                            (sol_parameter_id, PAR_value))
                        PAR_type = 'TUNNEL'
                        parameters.append(
                            (PAR_id, sol_parameter_id, PAR_type, sol_parameter_id,))
                        if PPV_optional_value != None:
                            parameter_definitions.append(
                                (sol_parameter_id, PAR_value, PPV_optional_value, PAR_id, sol_parameter_id, PAR_value))
            #SOL_tunnel_geom = MultiPoint(tunnel_points).wkb_hex
            for key, value in sol_parameter_list:
                if value != sol_parameters_dict[key]:
                    sol_parameters_dict[key].add(value)
        # SOL_VALUE
        for parameter_id in sol_parameters_dict:
            if re.search('Max', parameter_id):
                value = max(sol_parameters_dict[parameter_id])
            elif re.search('Min', parameter_id):
                value = min(sol_parameters_dict[parameter_id])
            elif parameter_id == 'ILL_GradProfile':
                parameter_values = [value.split(
                    '(') for value in sol_parameters_dict[parameter_id]]
                value = max(float(item[0]) for item in parameter_values)
            else:
                parameter_values = sol_parameters_dict[parameter_id]
                for value in parameter_values:
                    value = value
            sol_values.append((SOL_id, parameter_id, value,))
        return {
            'line': (LIN_id, LIN_name, self.__MEM_id),
            'sol': (SOL_id, SOL_length, SOL_nature, SOL_imcode, SOL_date_start, SOL_date_end, SOL_track_nb, SOL_tunnel_nb, OPP_start, OPP_end, self.__MEM_id, LIN_name,),
            'parameters': parameters,
            'parameter_definitions': parameter_definitions,
            'parameter_values': sol_values
        }

    def __insert_op(self, op_extract):
        # Insert the OP Type
        self.__insert(
            OP_TYPE_SQL_TEMPLATE, op_extract['op_type'])
        # Insert the OP
        self.__insert(OP_SQL_TEMPLATE, op_extract['op'])
        # Insert the OP's parameters
        for p in op_extract['parameters']:
            self.__insert(PARAMETER_SQL_TEMPLATE, p)
        for pd in op_extract['parameter_definitions']:
            self.__insert(
                PARAMETER_DEFINITION_SQL_TEMPLATE, pd)
        for pv in op_extract['parameter_values']:
            self.__insert(
                OPP_PARAMETER_VALUE_SQL_TEMPLATE, pv)

    def __extract_op(self, op):
        parameters = []
        parameter_definitions = []
        op_parameter_values = []
        # OPERATIONAL POINT TYPE
        OTY_id = op.find("OPType").get("Value")
        OTY_name = op.find("OPType").get("OptionalValue")
        # OPERATIONAL POINTS
        OPP_id = str(uuid.uuid4())  # BigAutoField
        OPP_uniqueid = op.find("UniqueOPID").get("Value")
        OPP_name = op.find("OPName").get("Value").replace("'", "''")
        OPP_taftapcode = op.find("OPTafTapCode").get("Value")
        OPP_lon = op.find("OPGeographicLocation").get(
            "Longitude").replace(",", ".")
        OPP_lat = op.find("OPGeographicLocation").get(
            "Latitude").replace(",", ".")
        OPP_date_start = op.get("ValidityDateStart")
        OPP_date_end = op.get("ValidityDateEnd")
        OPP_track_nb = 0
        OPP_tunnel_nb = 0
        OPP_platform_nb = 0
        geom = Point(float(OPP_lon), float(OPP_lat)).wkb_hex
        # COUNT OP TRACKS
        op_parameter_list = []
        op_parameters_dict = defaultdict(set)
        optracks = op.findall('OPTrack')
        for optrack in optracks:
            OPP_track_nb += 1
            # PARAMETERS
            op_parameters = optrack.findall('OPTrackParameter')
            for op_parameter in op_parameters:
                PAR_id = str(uuid.uuid4())
                op_parameter_id = op_parameter.get("ID")
                isapplicable = op_parameter.get("IsApplicable")
                if isapplicable == 'Y' and op_parameter_id in WANTED_PARAMETERS:
                    PAR_value = op_parameter.get("Value")
                    PPV_optional_value = op_parameter.get("OptionalValue")
                    op_parameter_list.append((op_parameter_id, PAR_value))
                    PAR_type = 'TRACK'
                    parameters.append(
                        (PAR_id, op_parameter_id, PAR_type, op_parameter_id,))
                    if PPV_optional_value != None:
                        parameter_definitions.append(
                            (op_parameter_id, PAR_value, PPV_optional_value, PAR_id, op_parameter_id, PAR_value))
            for key, value in op_parameter_list:
                if value != op_parameters_dict[key]:
                    op_parameters_dict[key].add(value)
            # COUNT OP TUNNELS
            optracktunnels = optrack.findall('OPTrackTunnel')
            for optunnel in optracktunnels:
                OPP_tunnel_nb += 1
                op_parameters = optunnel.findall('OPTrackTunnelParameter')
                for op_parameter in op_parameters:
                    PAR_id = str(uuid.uuid4())
                    op_parameter_id = op_parameter.get("ID")
                    isapplicable = op_parameter.get("IsApplicable")
                    if isapplicable == 'Y' and op_parameter_id in WANTED_PARAMETERS:
                        PAR_value = op_parameter.get("Value")
                        PPV_optional_value = op_parameter.get("OptionalValue")
                        op_parameter_list.append((op_parameter_id, PAR_value))
                        PAR_type = 'TUNNEL'
                        parameters.append(
                            (PAR_id, op_parameter_id, PAR_type, op_parameter_id,))
                        if PPV_optional_value != None:
                            parameter_definitions.append(
                                (op_parameter_id, PAR_value, PPV_optional_value, PAR_id, op_parameter_id, PAR_value))
                for key, value in op_parameter_list:
                    if value != op_parameters_dict[key]:
                        op_parameters_dict[key].add(value)
                # PARAMETERS
            optrackplatforms = optrack.findall('OPTrackPlatform')
            for opplatform in optrackplatforms:
                OPP_platform_nb += 1
                op_parameters = opplatform.findall('OPTrackPlatformParameter')
                for op_parameter in op_parameters:
                    PAR_id = str(uuid.uuid4())
                    op_parameter_id = op_parameter.get("ID")
                    isapplicable = op_parameter.get("IsApplicable")
                    if isapplicable == 'Y' and op_parameter_id in WANTED_PARAMETERS:
                        PAR_value = op_parameter.get("Value")
                        PPV_optional_value = op_parameter.get("OptionalValue")
                        PAR_type = 'PLATFORM'
                        parameters.append(
                            (PAR_id, op_parameter_id, PAR_type, op_parameter_id,))
                        op_parameter_list.append((op_parameter_id, PAR_value))
                        if PPV_optional_value != None:
                            parameter_definitions.append(
                                (op_parameter_id, PAR_value, PPV_optional_value, PAR_id, op_parameter_id, PAR_value))
                for key, value in op_parameter_list:
                    if value != op_parameters_dict[key]:
                        op_parameters_dict[key].add(value)
                # PARAMETERS
        # COUNT OP SIDING
        opsidings = op.findall('OPSiding')
        for opsiding in opsidings:
            op_parameters = opsiding.findall('OPSidingParameter')
            for op_parameter in op_parameters:
                PAR_id = str(uuid.uuid4())
                op_parameter_id = op_parameter.get("ID")
                isapplicable = op_parameter.get("IsApplicable")
                if isapplicable == 'Y' and op_parameter_id in WANTED_PARAMETERS:
                    PAR_value = op_parameter.get("Value")
                    PPV_optional_value = op_parameter.get("OptionalValue")
                    op_parameter_list.append((op_parameter_id, PAR_value))
                    PAR_type = 'TRACK'
                    parameters.append(
                        (PAR_id, op_parameter_id, PAR_type, op_parameter_id,))
                    if PPV_optional_value != None:
                        parameter_definitions.append(
                            (op_parameter_id, PAR_value, PPV_optional_value, PAR_id, op_parameter_id, PAR_value))
            for key, value in op_parameter_list:
                if value != op_parameters_dict[key]:
                    op_parameters_dict[key].add(value)

            # PARAMETERS

            opsidingtunnels = opsiding.findall('OPSidingTunnel')
            for opsidingtunnel in opsidingtunnels:
                OPP_tunnel_nb += 1

                op_parameters = opsidingtunnel.findall(
                    'OPSidingTunnelParameter')

                for op_parameter in op_parameters:
                    op_parameter_id = op_parameter.get("ID")
                    isapplicable = op_parameter.get("IsApplicable")

                    if isapplicable == 'Y' and op_parameter_id in WANTED_PARAMETERS:

                        PAR_value = op_parameter.get("Value")
                        PPV_optional_value = op_parameter.get("OptionalValue")
                        op_parameter_list.append((op_parameter_id, PAR_value))
                        PAR_type = 'TUNNEL'
                        parameters.append(
                            (PAR_id, op_parameter_id, PAR_type, op_parameter_id,))
                        if PPV_optional_value != None:
                            parameter_definitions.append(
                                (op_parameter_id, PAR_value, PPV_optional_value, PAR_id, op_parameter_id, PAR_value))

                for key, value in op_parameter_list:
                    if value != op_parameters_dict[key]:
                        op_parameters_dict[key].add(value)

        # OP_VALUE
        for parameter_id in op_parameters_dict:
            if re.search('Max', parameter_id):
                value = max(op_parameters_dict[parameter_id])
            elif re.search('Min', parameter_id):
                value = min(op_parameters_dict[parameter_id])
            else:
                parameter_values = op_parameters_dict[parameter_id]
                for value in parameter_values:
                    value = value
            op_parameter_values.append((value, OPP_id, parameter_id,))
        return {
            'op_type': (OTY_id, OTY_name, OTY_id),
            'op':  (OPP_id, OPP_name, OPP_uniqueid, OPP_lon, OPP_lat,geom, OPP_taftapcode, OPP_date_start, OPP_date_end, OPP_track_nb, OPP_tunnel_nb, OPP_platform_nb, OTY_id, self.__MEM_id),
            'parameters': parameters,
            'parameter_definitions': parameter_definitions,
            'parameter_values': op_parameter_values
        }

    def __insert(self, query_template, values):
        self.__postgres_cursor.execute('SAVEPOINT rinf_extractor')
        try:
            self.__postgres_cursor.execute(query_template, values)
            self.__total_rows += 1
        except psycopg2.IntegrityError:
            self.__postgres_cursor.execute('ROLLBACK TO SAVEPOINT rinf_extractor')
            self.__total_integrity_errors += 1
        finally:
            self.__postgres_cursor.execute('RELEASE SAVEPOINT rinf_extractor')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='rinf_to_postgres',
        description='parses a RINF XML file and imports data to a postgres database'
    )
    parser.add_argument('--rinf', help='path to the xml file', required=True)
    parser.add_argument('--postgres-host', help='hostname of the postgres server', required=True)
    parser.add_argument('--postgres-port', help='port number of the postgres server', required=True)
    parser.add_argument('--postgres-user', help='username of the postgres server', required=True)
    parser.add_argument('--postgres-password', help='password of the postgres server', required=True)
    parser.add_argument('--postgres-db', help='dbname of the postgres server', required=True)
    flags = parser.parse_args()
    config = RINFExtractorConfig(
        postgres_host=flags.postgres_host,
        postgres_port=int(flags.postgres_port),
        postgres_user=flags.postgres_user,
        postgres_password=flags.postgres_password,
        postgres_db=flags.postgres_db        
    )
    extractor = RINFExtractor(config)
    extractor_xml_file = extractor.parse_xml(flags.rinf)
    extractor_xml_file.close()
