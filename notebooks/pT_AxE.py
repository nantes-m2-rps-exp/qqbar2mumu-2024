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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ATTENTION CE CODE NE SERT A RIEN ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# %%
###################### Création d'une fonction qui calcul pT pour un run ############################
def pT_AxE (pT,pT_gen):
    """"Return the AxE for one run in function of pT """
    pT_f = ak.flatten(pT)  # Aplatir si c'est un awkward-array
    pT_gen_f = ak.flatten(pT_gen)  # Aplatir si c'est un awkward-array

    #On fait des bins de 1 en pT
    N_rec, Bins_rec = np.histogram(pT_f,bins=8,range = (0,8)) #N_rec est le nombre de Jpsi reconstruit dans chaque intervalle en pT
    N_gen, Bins_gen = np.histogram(pT_gen_f,bins=8,range = (0,8)) #N_gen est le nombre de Jpsi généré dans chaque intervalle en pT

    # Éviter les divisions par zéro (remplace les 0 par NaN pour les ignorer dans la moyenne)
    mask = (N_gen > 0)  # On garde uniquement les bins où il y a des J/ψ générés
    N_rec = N_rec[mask]
    N_gen = N_gen[mask]

    # Calcul des erreurs sur chaque bin
    err_N_rec = np.sqrt(N_rec)  # Erreur statistique (Poisson)
    err_N_gen = np.sqrt(N_gen)

    # **Moyenne pondérée avec les comptages comme poids**
    weights = N_gen  # Poids = Nombre de J/ψ générés
    N_rec_mean = np.sum(N_rec * weights) / np.sum(weights)
    N_gen_mean = np.sum(N_gen * weights) / np.sum(weights)
#  **Calcul de l'acceptance efficacité à partir des valeurs moyennées**
    acceptance_eff_mean = N_rec_mean / N_gen_mean
    err_acceptance_eff_mean = acceptance_eff_mean * np.sqrt(
        (np.sqrt(N_rec_mean) / N_rec_mean) ** 2 + (np.sqrt(N_gen_mean) / N_gen_mean) ** 2)


    return (acceptance_eff_mean, err_acceptance_eff_mean)

    

# %%
folder_path = "/pbs/throng/training/nantes-m2-rps-exp/data"
results = []
j_psi_gen = []
j_psi_rec = []
Acceptance_eff_pT = []
err_Acceptance_eff_pT = []

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
        #print("nMuonsGen = ", nMuonsGen)

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
        #print("nMuons = ", nMuons)

        #-------------------------------------Pour 5 fichier seulement---------a supprimer plus tard (supprimer l'affichage surtout)--------------------
        file_count += 1
        #file_count >= 5
        #if file_count > 2 :
           # print("Limite de fichiers atteinte.")
         #   break
            
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


#print("pT_rec : ", pT)
#print("pT_gen : ", pT_gen)
        
        # Appliquer le filtre de rapidité
        filtered_rec_events = masses_opposite[(y_pair <= -2.5) & (y_pair >= -4)]
        filtered_gen_events = jpsi_combi_gen[(y_gen <= -2.5) & (y_gen >= -4)]

        # Calcul de l'acceptance efficacité pour le run
        Acceptance_pT = pT_AxE(pT,pT_gen)[0]
        err_acceptance_pT = pT_AxE(pT,pT_gen)[1]

        Acceptance_eff_pT.append(Acceptance_pT)
        err_Acceptance_eff_pT.append(err_acceptance_pT)

        #print("nombre de Jpsi généré : ",len(filtered_gen_events))
        #print("nombre de Jpsi reconstruit : ",len(filtered_events))
        j_psi_gen.append(len(filtered_gen_events))
        j_psi_rec.append(len(filtered_events))

Acceptance_eff_pT = np.array(Acceptance_eff_pT)
err_Acceptance_eff_pT = np.array(err_Acceptance_eff_pT)
print("acceptance efficacité pour les différents run : ", Acceptance_eff_pT)
print("erreur sur l'acceptance efficacité pour les différents run : ", err_Acceptance_eff_pT)


#print(results)
#print(pT)

# %%
######################################### test de la fonction ######################################
Acceptance = pT_AxE(pT,pT_gen)[0]
err_acceptance = pT_AxE(pT,pT_gen)[1]
print(Acceptance, '+/-', err_acceptance)

# %%
##################################### évolution de l'acceptance efficacité en fonction de pT ######################################
pT_f = ak.flatten(pT)  # Aplatir si c'est un awkward-array
N_rec, Bins_rec = np.histogram(pT_f,bins=8,range = (0,8)) #N_rec est le nombre de Jpsi reconstruit dans chaque intervalle en pT
print(len(Bins_rec))
print(len(Acceptance_eff_pT))
plt.figure()       
plt.errorbar(Bins_rec[:-1],Acceptance_eff_pT, yerr=err_Acceptance_eff_pT, fmt='+',color = 'purple', label = 'erreur')
width = 8/len(Bins_rec[:-1])
plt.bar(Bins_rec[:-1], Acceptance_eff_pT,width = width, edgecolor='black', color='skyblue')
#plt.hist(Bins_rec[1:])
plt.plot(Bins_rec[:-1], Acceptance_eff_pT,'r')
plt.xlabel('pT (GeV)')
plt.ylabel("Acceptance efficacité")
plt.title("Evolution de l'acceptance efficacité en fonction de pT (GeV)")
plt.grid(True)
plt.show()

# %%

# %%
