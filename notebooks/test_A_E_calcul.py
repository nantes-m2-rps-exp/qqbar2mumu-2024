# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import uproot
import awkward as ak
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import math
import hist
import vector
import os
import subprocess
import gc
from scipy.optimize import curve_fit
print("uproot version",uproot.__version__)
print("awkward version",ak.__version__)
print("numpy version",np.__version__)
print("matplotlib version",matplotlib.__version__)
print("hist version",hist.__version__)
print("vector version",vector.__version__)

vector.register_awkward()


# %% [markdown]
# ## Fonction de calcul de l'acceptance efficacité

# %%
###################### Création d'une fonction qui calcul AxE pour un run ############################
def A_E(y_rec: ak.Array, y_gen: ak.Array, nBins: int = 5): # j'ai rajouté un paramètre nBins pour facilement ajuster le nombre de bins pris en compte
    """Return the acceptance efficiency for one run and the associated error"""
    # Appliquer le filtre de rapidité
    filtered_y_rec = y_rec[(y_rec <= -2.5) & (y_rec >= -4) 
                            & (pT >= 0) & (pT <= 1)] #si on veut avoir l'acceptance efficacité que dans une certaine range en pT
    y_rec_f = ak.flatten(filtered_y_rec)  #applatir les données pour l'histo

    filtered_y_gen = y_gen[(y_gen <= -2.5) & (y_gen >= -4)
                            & (pT_gen >= 0) & (pT_gen <= 1)] #si on veut avoir l'acceptance efficacité que dans une certaine range en pT

    y_gen_f = ak.flatten(filtered_y_gen)  #applatir les données pour l'histo

    # Histogrammes pour la rapidité des J/ψ reconstruits et générés
    yN_rec, yBins_rec = np.histogram(y_rec_f, bins=nBins)
    yN_gen, yBins_gen = np.histogram(y_gen_f, bins=nBins)

    # Éviter les divisions par zéro (remplace les 0 par NaN pour les ignorer dans la moyenne)
    mask = (yN_gen > 0)  # On garde uniquement les bins où il y a des J/ψ générés
    yN_rec = yN_rec[mask]
    yN_gen = yN_gen[mask]

    # Calcul des erreurs sur chaque bin
    err_N_rec_y = np.sqrt(yN_rec)  # Erreur statistique (Poisson)
    err_N_gen_y = np.sqrt(yN_gen)

    # **Moyenne pondérée avec les comptages comme poids**
    weights = yN_gen  # Poids = Nombre de J/ψ générés
    yN_rec_mean = np.sum(yN_rec * weights) / np.sum(weights)
    yN_gen_mean = np.sum(yN_gen * weights) / np.sum(weights)

    #  **Calcul de l'acceptance efficacité à partir des valeurs moyennées**
    acceptance_eff_mean = yN_rec_mean / yN_gen_mean
    err_acceptance_eff_mean = acceptance_eff_mean * np.sqrt(
        1 / yN_rec_mean + 1 / yN_gen_mean)

    return (acceptance_eff_mean, err_acceptance_eff_mean)


# %% [markdown]
# ## Calcul de l'acceptance efficacité sur les runs

# %% [markdown]
# Sélection des runs

# %%
runs = [291263] # spécifie les runs auquels on s'intéresse

def return_files(iRuns: list[int]): 
    ## donne les chemins d'accès aux fichiers correspondant aux runs spécifiés
    folder_path = "/pbs/throng/training/nantes-m2-rps-exp/data"
    out: list[str] = []
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".mc.root"):
            if int(file_name[3:-8]) in runs:
                print(file_name, " found")
                out.append(os.path.join(folder_path, file_name))
    return out

file_paths = return_files(runs)

# %%
results: dict = {}

for f in file_paths:
    nRun = int(f.split('/')[-1][3:-8]) # récupère le numéro du run pour l'initialiser dans les résultats
    results[nRun] = {}

    print(f">>> Traitement du fichier : {f.split('/')[-1]}")
    file = uproot.open(f)

    gen = file["genTree"]   # fetch generated muons
    n = gen.arrays([
        "nMuonsGen",
        "Muon_GenPx",
        "Muon_GenPy",
        "Muon_GenPz",
        "Muon_GenE",
        "Muon_GenLabel",
        "Muon_GenMotherPDGCode"
    ])

    nMuonsGen = 0
    for i in range(len(n)):
        info = n[i]["nMuonsGen"]
        nMuonsGen += info
    print("\tnMuonsGen = ", nMuonsGen)

    events = file["eventsTree"] # fetch reconstructed muons
    m = events.arrays([
        "zVtx",
        "isCMUL",
        "nMuons",
        "Muon_Px",
        "Muon_Py",
        "Muon_Pz",
        "Muon_E",
        "Muon_Charge",
        "Muon_thetaAbs",
        "Muon_matchedTrgThreshold",
        "Muon_MCLabel"
    ])
    
    nMuons = 0
    for i in range(len(m)):
        info = m[i]["nMuons"]
        nMuons += info
    print("\tnMuons = ", nMuons)
    
            
    mask = (m["nMuons"] >= 2) & ak.all(n["Muon_GenMotherPDGCode"] == 443, axis=1)  # filter for dimuons (or more) with mother Jpsi
    filtered_gen_events = n[ak.all(n["Muon_GenMotherPDGCode"] == 443, axis=1)]
    filtered_events = m[mask & (m.isCMUL)&(abs(m.zVtx)<10)]                        # additional filter for reconstruction of Cmul trigger and zVtx?

    
    muon_vectors1 = ak.zip(                                                        # Initialiser les vecteurs des muons
        {
            "px": filtered_events.Muon_Px,
            "py": filtered_events.Muon_Py,
            "pz": filtered_events.Muon_Pz,
            "E": filtered_events.Muon_E,
            "matchedTrgThreshold": filtered_events.Muon_matchedTrgThreshold,
            "charge": filtered_events.Muon_Charge,
            "theta": filtered_events.Muon_thetaAbs,
        },
        with_name="Momentum4D",
    )
           
    jpsi_combi = ak.combinations(muon_vectors1, 2, fields=["muon1", "muon2"])        # Combinaisons de paires
    
    opposite_charge_pairs = jpsi_combi[                                              # Paires de charges opposées et filtrage
        (jpsi_combi.muon1.charge != jpsi_combi.muon2.charge)
        & (jpsi_combi.muon1.matchedTrgThreshold == 2)
        & (jpsi_combi.muon2.matchedTrgThreshold == 2)
        & (jpsi_combi.muon1.theta <= 10)
        & (jpsi_combi.muon2.theta <= 10)
        & (jpsi_combi.muon1.theta >= 3)
        & (jpsi_combi.muon2.theta >= 3)
        & (jpsi_combi.muon1.eta <= -2.5)  # ici on a un premier filtre en rapidité
        & (jpsi_combi.muon1.eta <= -2.5)
        & (jpsi_combi.muon2.eta >= -4)
        & (jpsi_combi.muon2.eta >= -4)
    ]
        
    # Calcul des masses invariantes et de la rapidité
    masses_opposite = (opposite_charge_pairs.muon1 + opposite_charge_pairs.muon2).mass
    y_pair = (opposite_charge_pairs.muon1 + opposite_charge_pairs.muon2).rapidity
    #print("y_pair =", y_pair)

    ################################### calcul du pT pour les Jpsi reconstruit ###################################
    pT = (opposite_charge_pairs.muon1 + opposite_charge_pairs.muon2).pt

    ################################### calcul du pT pour les Jpsi généré ###################################
    muon_vectors_gen = ak.zip({
        "px": filtered_gen_events.Muon_GenPx,
        "py": filtered_gen_events.Muon_GenPy,
        "pz": filtered_gen_events.Muon_GenPz,
        "E": filtered_gen_events.Muon_GenE
    }, with_name="Momentum4D")

    jpsi_combi_gen = ak.combinations(muon_vectors_gen, 2, fields=["muonA", "muonB"])
    pT_gen = (jpsi_combi_gen.muonA + jpsi_combi_gen.muonB).pt
    y_gen = (jpsi_combi_gen.muonA + jpsi_combi_gen.muonB).rapidity

    #print("y_gen =", y_gen)
        
    # Appliquer le filtre de rapidité                    (2ème filtre en rapidité?)
    filtered_rec_events = masses_opposite[(y_pair <= -2.5) & (y_pair >= -4)]
    filtered_gen_events = jpsi_combi_gen[(y_gen <= -2.5) & (y_gen >= -4)]


    # Enregistrement des résultats
    results[nRun]["gen_Jpsi"] = len(filtered_gen_events)
    results[nRun]["rec_Jpsi"] = len(filtered_events)
    results[nRun]["A_E"], results[nRun]["errA_E"] = A_E(y_pair,y_gen, 5) # ici la fonction A_E applique un troisième filtre en rapidité?

    print("\tnombre de Jpsi généré :",results[nRun]["gen_Jpsi"])
    print("\tnombre de Jpsi reconstruit :",results[nRun]["rec_Jpsi"])
    print("\tAcceptance efficacité :", round(results[nRun]["A_E"], 6),"±", round(results[nRun]["errA_E"], 6)) # résultat arrondi pour être lisible


# %% [markdown]
# Moyenne des acceptances efficacités en utilisant le nombre de Jpsi générés comme poids

# %%
val: float = 0
err: float = 0

norm = 0
for r in results.keys(): norm+=results[r]["gen_Jpsi"]

for r in results.keys():
    val += results[r]["gen_Jpsi"]/norm * results[r]["A_E"]
    err += pow( results[r]["gen_Jpsi"]/norm * results[r]["errA_E"]/results[r]["A_E"] , 2 )
err = val * np.sqrt(err)

print(round(val, 6), "±", round(err, 6))

# %% [markdown]
# \
# \
# J'ai pas regardé la partie ci-après

# %%
# Appliquer le filtre de rapidité
filtered_y_rec = y_pair[(y_pair <= -2.5) & (y_pair >= -4)]
y_rec_f = ak.flatten(filtered_y_rec)

filtered_y_gen = y_gen[(y_gen <= -2.5) & (y_gen >= -4)]
y_gen_f = ak.flatten(filtered_y_gen)

print("rapidité filtré des jpsi reconstruit : ",y_rec_f)
print("rapidité filtré des jpsi généré : ",y_gen_f)

#histo pour la rapidité des jpsi reconstruit
yN_rec, yBins_rec = np.histogram(y_rec_f,bins=50) #yN_rec est le nombre de Jpsi reconstruit dans chaque intervalle en y
print("y_rec = ", yBins_rec)
print("yN_rec = ",yN_rec)
#histo pour la rapidité des jpsi généré
yN_gen, yBins_gen = np.histogram(y_gen_f,bins=50) #yN_rec est le nombre de Jpsi reconstruit dans chaque intervalle en y
print("y_gen = ", yBins_gen)

# %%
# Affichage de l'histogramme
plt.hist(y_rec_f, bins=50, density=False, alpha=0.7, color='b', edgecolor='black')
# Ajout des labels et du titre
plt.xlabel("Rapidité de la paire de muons reconstruit")
plt.ylabel("Nombre de J/psi")
plt.title("Distribution de la rapidité des paires de muons reconstruit")
plt.grid(True)
plt.savefig("ydistrib_mu_rec.pdf")

# %%
# Affichage de l'histogramme
plt.hist(y_gen_f, bins=50, density=False, alpha=0.7, color='b', edgecolor='black')
# Ajout des labels et du titre
plt.xlabel("Rapidité de la paire de muons généré")
plt.ylabel("Nombre de Jpsi")
plt.title("Distribution de la rapidité des paires de muons généré")
plt.grid(True)
plt.savefig("ydistrib_mu_gen.pdf")

# %%
y_pair_f = ak.flatten(y_pair)

yN_pair, yBins_pair = np.histogram(y_pair_f,bins=50) #yN_rec est le nombre de Jpsi reconstruit dans chaque intervalle en y

# Affichage de l'histogramme
plt.hist(y_pair_f, bins=50, density=False, alpha=0.7, color='b', edgecolor='black')
# Ajout des labels et du titre
plt.xlabel("Rapidité de la paire de muons reconstruit")
plt.ylabel("Nombre de Jpsi")
plt.title("Distribution de la rapidité des paires de muons reconstruit")
plt.grid(True)

# %%
