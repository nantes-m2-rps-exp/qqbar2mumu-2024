# Introduction (trop) rapide à Git

Les concepts sous-jacents à Git seront abordés plus en détail en séance.
Ci-dessous un résumé des commandes que vous utiliserez le plus souvent.

## Téléchargement du dépôt git du projet

Utiliser la commande git suivante :

```shell
git clone https://github.com/nantes-m2-rps-exp/qqbar2mumu-2024.git
```

Par défault, vous êtes sur la branche `main`.
 Vous n'avez pas les droits requis pour modifier cette branche (qui est considérée comme la "branche de référence").

## Création d'une branche

Pour pouvoir travailler sur le projet, vous devez d'abord créer une branche : 

```shell
git checkout -b nom_de_la_branche
```

Vous êtes alors automatiquement positionné sur votre branche. Il est conseillé de choisir un nom de branche permettant d'identifier le créateur et contenant une indication sur la tâche que vous souhaitez réaliser sur cette branche. Par exemple un nom de branche pourrait être "guilbaud_distmasseinvariante". Pour lister les branches disponibles :

```shell
git branch 
```

## Changement de branche

Pour changer de branche :

```shell
git switch "BRANCH_NAME"
```

## Ajouter des modifications (commit)

Vous pouvez maintenant commencer à travailler. Pour sauvegarder en local les changements sur vos fichiers, il faut utiliser les commandes :

```shell
git add "FICHIER-X" "FICHIER-Y" "FICHIER-Z"
git commit -m "your message that explains what you have changed" 
```

Pour savoir quels fichiers ont été modifiés et ne sont pas encore sauvegardés par un commit :

```shell
git status
```

Il est important de faire des "commit" le plus régulièrement possible. Cela permet de sauvegarder tous vos changements, de revenir en arrière, etc. 

## Sauvegarder les modifications (push)

Lorsque vous êtes satisfait de votre avancée et à intervalle plus ou moins régulier, vous pouvez envoyer votre code sur le dépôt distant.

Pour cela :

```shell
git push
```

> Lors de votre tout premier push git va vous demander d'enregister quelques informations (les instructions à entrer sont fournis par git). 

Pour n'importe quel push, vous devez être en mesure de vous authentifier auprès de git. Depuis une ligne de commande comme indiqué ci-dessus cela ne peut se faire que par l'utilisation d'un [token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic).

> Attention, ce token n'a rien à voir avec votre mot de passe d'accès à github.


## Pull request 

Une fois la tâche terminée, pour intégrer vos changements à la branche `main` du projet, il vous faudra faire une "pull request" en ligne. Plus de détails en séance.

## Git et les notebooks Jupyter

Les fichiers correspondant aux notebooks Jupyter (fichiers d'extension `.ipynb`) changent dès lors qu'ils sont executés, même si aucune des cellules dont vous êtes les autres (cellules de code et/ou de texte) ne changent. Or, tout changement est détecté par Git comme un nouveau changement sur lequel il faudrait faire une séquence `git add; git commit -m;` (puis un `git push` à un moment donné). Ce n'est (généralement) pas ce que vous voulez. Vous souhaitez plutôt n'enregistrer que les modifications "utiles", celle qui correspondent aux cellules que vous avez rédigées, et non celles qui sont générées.

Pour résoudre ce problème il existe un outil Python, [nbstripout](https://github.com/kynan/nbstripout) qui fait un nettoyage des fichiers notebook. Nous vous conseillons de l'utiliser pour avoir un historique plus "propre" de vos branches.

Depuis [l'interface Jupyter](https://notebook.cc.in2p3.fr), ouvrez un terminal (File>New>Terminal). Pour installer l'outil la première fois, exécutez :

```shell
pip install --user nbstripout
```

Ensuite, juste avant de committer un changement dans un notebook `mon_notebook.ipynb`, exécutez : 

```shell
cd notebooks
$HOME/.local/bin/nbstripout --keep-id mon_notebook.ipynb
```
