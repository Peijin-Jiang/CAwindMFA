# loop tp from 0 to 2

for tp in {0..2}
do
    for scen in 'Gcam' 'GNZ'
    do
    echo "Running experiments for TP $tp and scenario $scen"
    python a_capacity_flow.py --tp $tp --scen $scen
    python d_offshore_env_impact.py --tp $tp --scen $scen
    python c_offshore_EoL.py --tp $tp --scen $scen
    python b_offshore_material.py --tp $tp --scen $scen
    python d_onshore_env_impact.py --tp $tp --scen $scen
    python c_onshore_EoL.py --tp $tp --scen $scen
    python b_onshore_material.py --tp $tp --scen $scen
    python d_total_env_impact.py --tp $tp --scen $scen
    done
done
