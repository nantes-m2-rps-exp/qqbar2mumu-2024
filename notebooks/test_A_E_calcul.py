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

# %%
folder_path = "/pbs/throng/training/nantes-m2-rps-exp/data"
results = []
j_psi_gen = []
j_psi_rec = []

file_count =0

for file_name in os.listdir(folder_path):
    if file_name.endswith(".mc.root"):
        file_path = os.path.join(folder_path, file_name)
        results.append(file_name[0:-8])

        print(f"Traitement du fichier : {file_name}")
        file = uproot.open(file_path)

        gen = file["genTree"]
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
        print("nMuonsGen = ", nMuonsGen)

        events = file["eventsTree"]
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
        print("nMuons = ", nMuons)

        #-------------------------------------Pour 5 fichier seulement---------a supprimer plus tard (supprimer l'affichage surtout)--------------------
        file_count += 1
        #file_count >= 5
        if file_count > 3 :
           # print("Limite de fichiers atteinte.")
            break
            
        mask = (m["nMuons"] >= 2) & ak.all(n["Muon_GenMotherPDGCode"] == 443, axis=1)
        filtered_gen_events = n[ak.all(n["Muon_GenMotherPDGCode"] == 443, axis=1)]
        filtered_events = m[mask & (m.isCMUL)&(abs(m.zVtx)<10)]

                # Initialiser les vecteurs des muons
        muon_vectors1 = ak.zip(
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
                # Combinaisons de paires
        jpsi_combi = ak.combinations(muon_vectors1, 2, fields=["muon1", "muon2"])
        
        # Paires de charges opposées et filtrage
        opposite_charge_pairs = jpsi_combi[
            (jpsi_combi.muon1.charge != jpsi_combi.muon2.charge)
            & (jpsi_combi.muon1.matchedTrgThreshold == 2)
            & (jpsi_combi.muon2.matchedTrgThreshold == 2)
            & (jpsi_combi.muon1.theta <= 10)
            & (jpsi_combi.muon2.theta <= 10)
            & (jpsi_combi.muon1.theta >= 3)
            & (jpsi_combi.muon2.theta >= 3)
            & (jpsi_combi.muon1.eta <= -2.5)
            & (jpsi_combi.muon1.eta <= -2.5)
            & (jpsi_combi.muon2.eta >= -4)
            & (jpsi_combi.muon2.eta >= -4)
        ]
        
        # Calcul des masses invariantes et de la rapidité
        masses_opposite = (opposite_charge_pairs.muon1 + opposite_charge_pairs.muon2).mass
        y_pair = (opposite_charge_pairs.muon1 + opposite_charge_pairs.muon2).rapidity
        print("y_pair =", y_pair)

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

        print("y_gen =", y_gen)


#print("pT_rec : ", pT)
#print("pT_gen : ", pT_gen)
        
        # Appliquer le filtre de rapidité
        filtered_rec_events = masses_opposite[(y_pair <= -2.5) & (y_pair >= -4)]
        filtered_gen_events = jpsi_combi_gen[(y_gen <= -2.5) & (y_gen >= -4)]


        print("nombre de Jpsi généré : ",len(filtered_gen_events))
        print("nombre de Jpsi reconstruit : ",len(filtered_events))
        j_psi_gen.append(len(filtered_gen_events))
        j_psi_rec.append(len(filtered_events))

#print(results)
#print(pT)


# %%
###################### Création d'une fonction qui calcul AxE pour un run ############################
def A_E(y_rec, y_gen):
    """Return the acceptance efficiency for one run and the associated error"""
    # Appliquer le filtre de rapidité
    filtered_y_rec = y_rec[(y_rec <= -2.5) & (y_rec >= -4)]
    y_rec_f = ak.flatten(filtered_y_rec)  #applatir les données pour l'histo

    filtered_y_gen = y_gen[(y_gen <= -2.5) & (y_gen >= -4)]
    y_gen_f = ak.flatten(filtered_y_gen)  #applatir les données pour l'histo

    #histo pour la rapidité des jpsi reconstruit
    yN_rec, yBins_rec = np.histogram(y_rec_f,bins=50) #yN_rec est le nombre de Jpsi reconstruit dans chaque intervalle en y
    #histo pour la rapidité des jpsi généré
    yN_gen, yBins_gen = np.histogram(y_gen_f,bins=50) #yN_rec est le nombre de Jpsi reconstruit dans chaque intervalle en y

    err_N_rec_y = np.sqrt(yN_rec)
    err_N_gen_y = np.sqrt(yN_gen)

    # Calcul de l'acceptance efficacité et son erreur pour chaque bin en rapidité entre 2.5 et 4
    acceptance_eff_y = yN_rec / yN_gen  # Converti automatiquement en array NumPy
    err_acceptance_eff_y = acceptance_eff_y * np.sqrt((err_N_rec_y / yN_rec) ** 2 + (err_N_gen_y / yN_gen) ** 2)

    # Calcul de la moyenne pondérée
    weights = 1 / err_acceptance_eff_y**2  # Poids = 1/sigma^2 (array NumPy)
    acceptance_eff_mean = np.nansum(acceptance_eff_y * weights) / np.nansum(weights)
    err_acceptance_eff_mean = np.sqrt(1 / np.nansum(weights))
    return (acceptance_eff_mean, err_acceptance_eff_mean)


# %%
######################################### test de la fonction ######################################
Acceptance = A_E(y_pair,y_gen)[0]
err_acceptance = A_E(y_pair,y_gen)[1]
print(Acceptance, '+/-', err_acceptance)

# %%
