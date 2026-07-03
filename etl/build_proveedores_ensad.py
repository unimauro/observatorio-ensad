import json
rows=json.load(open('ensad_rows.json'))
def tp(ruc):
    return 'empresa' if ruc[:2]=='20' else ('natural' if ruc[:2] in ('10','15') else 'empresa')
duenos={
 '20110401796': ("Fabiola Maria Leon Velarde Servetto (Presidente, desde 2023-12-02); Asociacion cultural sin fines de lucro",
                 "https://www.datosperu.org/empresa-alianza-francesa-de-lima-20110401796.php"),
 '10078295525': ("Persona natural (proveedor directo); arrendo el inmueble Teatro Roma a la ENSAD",
                 "https://infodelperu.com/zanatti-berninzon-carlos-alberto-10078295525/"),
}
agg={}
for r in rows:
    ruc=r['ruc_proveedor']; a=agg.setdefault(ruc,{
        'nombre':r['proveedor'],'ruc':ruc,'monto':0.0,'convs':set(),
        'tipos':{},'objeto':{},'tipo_persona':tp(ruc),
        'tipo_proveedor_seace':r['tipo_proveedor']})
    a['monto']+=float(r['monto_adjudicado_item_soles'])
    a['convs'].add(r['codigoconvocatoria'])
    a['tipos'][r['tipoprocesoseleccion']]=a['tipos'].get(r['tipoprocesoseleccion'],0)+1
    a['objeto'][r['objetocontractual']]=a['objeto'].get(r['objetocontractual'],0)+1
provs=[]
for ruc,a in agg.items():
    d,f=duenos.get(ruc,(None,None))
    provs.append({'nombre':a['nombre'],'ruc':ruc,'monto':round(a['monto'],2),
        'n':len(a['convs']),'tipos':a['tipos'],'objeto':a['objeto'],
        'tipo_persona':a['tipo_persona'],'tipo_proveedor_seace':a['tipo_proveedor_seace'],
        'dueno':d,'fuente_dueno':f})
provs.sort(key=lambda x:-x['monto'])
monto_total=round(sum(p['monto'] for p in provs),2)
emp=[p for p in provs if p['tipo_persona']=='empresa']
nat=[p for p in provs if p['tipo_persona']=='natural']
all_convs=set(r['codigoconvocatoria'] for r in rows)
top_personas=sorted([{'nombre':p['nombre'],'ruc':p['ruc'],'monto':p['monto'],'n':p['n']} for p in nat],key=lambda x:-x['monto'])
out={
 '_meta':{
  'fuente':'OECE/OSCE - CONOSCE Datos Abiertos, reporte de Adjudicaciones (buena pro por item)',
  'fuente_url':'https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/adjudicaciones/',
  'entidad':'Escuela Nacional Superior de Arte Dramatico "Guillermo Ugarte Chamorro" (ENSAD) - UE 123 pliego 010 MINEDU',
  'ruc':'20600739159',
  'codigoentidad_conosce':202366,
  'periodo':'2023-2025',
  'extraido':'2026-07',
  'unidad_monto':'Soles (PEN), monto adjudicado por item',
  'nota':'Agregado desde reportes anuales CONOSCE de Adjudicaciones (nivel item de buena pro), archivos CONOSCE_ADJUDICACIONES{2023,2024,2025}_0.xlsx. ENSAD es una entidad muy pequena: en 2023-2025 solo registra 2 adjudicaciones (1 en 2023, 1 en 2024, 0 en 2025), ambas Contrataciones Directas de alquiler de inmueble (Teatro Roma y sede via Alianza Francesa). "monto"=suma de monto_adjudicado_item_soles. "n"=numero de codigoconvocatoria distintos. tipo_persona por prefijo de RUC (20=empresa/asociacion, 10/15=natural). NO incluye ordenes de compra <8 UIT (dataset aparte). En 2025 el reporte CONOSCE no lista adjudicaciones para el codigoentidad 202366.'
 },
 'totales':{
  'monto_total':monto_total,
  'n_proveedores':len(provs),
  'n_procesos':len(all_convs),
  'n_empresas':len(emp),
  'n_personas_naturales':len(nat),
  'monto_empresas':round(sum(p['monto'] for p in emp),2),
  'monto_personas_naturales':round(sum(p['monto'] for p in nat),2),
 },
 'top_personas':top_personas,
 'proveedores':provs,
}
json.dump(out, open('/Users/unimauro/Documents/Repos/observatorio-ensad/data/proveedores-ensad.json','w'),
          ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
