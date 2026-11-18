# Hallazgos del EDA (fuente: backend/eda/*.txt, *.csv; verificado en parte por Samuel)

## Críticos
- El evento `pass_outcome_caught` aparece solo en 23 de 4620 pases completos. No sirve como momento de evaluación.
- El tracking termina 5 frames (0.5 s) después de `pass_forward` en todos los pases revisados (25 de 122 archivos).
  Por tanto no hay YAC ni posición de captura en el tracking. `yac_tracking` ≈ 0 (correlación 0.002 con el resultado).
- Momento de evaluación adoptado: último frame de cada pase (pass_forward + 5 frames), con pase en el aire.
- Valor del pase para la ofensiva: prePenaltyPlayResult si es completo (C), 0 si es incompleto (I) o intercepción (IN).
  En C el valor va de -8 a 91, media 12.1. S (sacks) y R (scrambles) no tienen receptor objetivo: se excluyen.

## Datos
- Jugadas: C 4620, I 2755, S 543, R 449, IN 190. Jugadas "No Play" (castigo): 489, se excluyen.
- Receptor objetivo: sale de playDescription ("to X.Apellido", ~81% de las jugadas coinciden con el patrón);
  se resuelve a nflId entre los jugadores ofensivos de la jugada con la función `resolver` de backend/eda/resultados_defensivos.py.
- Defensor más cercano al receptor: entre jugadores con pff_role Coverage o Pass Rush (en esta muestra, no siempre es Coverage).
- Dirección: playDirection 'left' o 'right'. En 'left' la ofensiva está a la derecha del balón (x media +1.5) y en 'right'
  a la izquierda (-1.5). Normalizar a ataque hacia x creciente: si left, x = 120 - x, y = 53.3 - y, dir y o rotan 180°.
- Posiciones: CB, FS, SS, OLB, ILB, MLB, DE, DT, NT. Hay 613 defensores con al menos un evento atribuido.

## Atribución de resultados a defensores (backend/eda/defensores_resultados.csv)
- Cobertura: intercepciones 100%, incompletos con defensor nombrado 27.6%, completos con tacleador nombrado 83.1%.
- Columnas: nflId, displayName, officialPosition, defensiveTeam, intercepciones, incompletos_defendidos, fumbles_forzados,
  fumbles_recuperados, jugadas_negativas_para_ofensiva, completos_tacleados. Se usa como panel "boxscore" del perfil.
- completos_tacleados es una aproximación de "completo permitido", no cobertura real.
- 8 nombres sin resolver de 5196 (por ejemplo "Qu.Williams"); se ignoran.

## Decisiones tomadas
- Mínimo de pases por defensor para entrar al ranking: 15 (pases donde es el defensor más cercano al receptor). Es el valor por defecto de `min_plays`.
- Solo se cuentan los pases donde el defensor más cercano está a 10 yardas o menos del receptor. El resto se descarta en precompute.py.
- Valor de una intercepción: 0 yardas (igual que un incompleto).
- No hay división entrenamiento/prueba por semanas. Los modelos kNN se evalúan con leave-one-out: al predecir un pase se excluye ese mismo pase de los vecinos.
- Posiciones a mostrar en el ranking (T0): CB, FS, SS, ILB, MLB, OLB. Por defecto el filtro va en CB, FS y SS. DE, DT y NT se excluyen (rushers, 0 a 3 intercepciones y pocos pases cubiertos). DB y RB (1 jugador cada uno, 0 intercepciones) se excluyen por ser ruido.
