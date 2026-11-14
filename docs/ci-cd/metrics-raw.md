# Сирі дані метрик CI/CD (Metrics Raw Data)

Цей документ містить зібрані первинні дані історії запусків CI/CD конвеєра для розрахунку чотирьох метрик DORA відповідно до **Етапу 1 («Збір даних»)** лабораторної роботи «Клініка продуктивності CI/CD».

## 1. Методологія збору даних

- **Репозиторій**: `ukma-fin-ssdm-2026/ctrl-alt-defeat`
- **Гілка**: `main`
- **Врахований workflow**: `CI Test` (`.github/workflows/ci.yml`) — комплексний конвеєр автоматичного тестування (pytest, vitest, ruff, black, docker build, reliability checks).
- **Період вибірки**: **з 01.11.2026 по 13.11.2026** (загалом **98 запусків на main**, охоплює релізи, лабораторні роботи та дедлайн 1 листопада).
- **Визначення розгортання (deployment)**: згідно з концепцією безперервної доставки (Continuous Delivery), кожна зелена збірка на `main` готова до випуску і вважається розгортанням.
- **Час у черзі (queue time)**: інтервал від створення запуску (`createdAt`) до початку першого завдання (`startedAt` у `jobs`).
- **Час виконання (execution time)**: інтервал від старту першого завдання (`startedAt`) до завершення останнього (`completedAt`).
- **Час виконання змін (change lead time)**: інтервал від першого коміту в Pull Request (`authoredDate` першого коміту в PR) до завершення зеленого запуску на `main`.
- **Джерело доказів**: експорт GitHub Actions збережено у файлах:
  - [`docs/ci-cd/evidence/gh-runs-raw.json`](docs/ci-cd/evidence/gh-runs-raw.json) — детальні дані по кожному запуску (jobs, commits, lead times);
  - [`docs/ci-cd/evidence/gh-run-list-since-nov01.json`](docs/ci-cd/evidence/gh-run-list-since-nov01.json) — прямий JSON-дамп команди `gh run list`.

## 2. Первинні дані запусків з 01.11 (Таблиця Етапу 1)

| № | Коміт | PR | Перший коміт PR | Запуск завершено | Черга, хв | Виконання, хв | Статус |
|---|---|---|---|---|:---:|:---:|:---:|
| 1 | [`f248673`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43407945717) | #234 | 13.11 00:14 | 13.11 10:19 | 0.1 | 2.9 | ✅ |
| 2 | [`113cbf8`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43334770926) | #233 | 13.11 00:05 | 13.11 00:11 | < 0.1 | 2.3 | ✅ |
| 3 | [`e651885`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43333465657) | #232 | 12.11 23:27 | 13.11 00:02 | < 0.1 | 2.6 | ✅ |
| 4 | [`082bfdd`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43333055330) | #231 | 12.11 23:11 | 12.11 23:58 | < 0.1 | 1.8 | ✅ |
| 5 | [`b80c5e2`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43324531738) | #230 | 12.11 22:51 | 12.11 22:59 | < 0.1 | 2.1 | ✅ |
| 6 | [`1d17f98`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43323764490) | #229 | 12.11 22:42 | 12.11 22:54 | < 0.1 | 2.5 | ✅ |
| 7 | [`d1265e0`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43321665369) | #228 | 12.11 22:26 | 12.11 22:40 | < 0.1 | 2.2 | ✅ |
| 8 | [`ac88350`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43319544872) | #226 | 12.11 22:13 | 12.11 22:26 | < 0.1 | 2.6 | ✅ |
| 9 | [`5a9eb84`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43319138050) | #225 | 12.11 22:13 | 12.11 22:24 | < 0.1 | 2.7 | ✅ |
| 10 | [`2eded36`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43225429400) | #224 | 12.11 12:13 | 12.11 13:17 | 0.1 | 2.5 | ✅ |
| 11 | [`8182909`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43209933197) | #222 | 12.11 10:21 | 12.11 11:34 | < 0.1 | 2.7 | ✅ |
| 12 | [`492899e`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43208914412) | #223 | 12.11 11:21 | 12.11 11:26 | < 0.1 | 2.0 | ✅ |
| 13 | [`1d5376a`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43062571852) | #221 | 11.11 16:48 | 11.11 16:54 | < 0.1 | 2.5 | ✅ |
| 14 | [`c31ebbd`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43058044499) | #220 | 11.11 16:19 | 11.11 16:26 | < 0.1 | 2.1 | ✅ |
| 15 | [`065b832`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43049671107) | #219 | 11.11 15:30 | 11.11 15:36 | < 0.1 | 2.1 | ✅ |
| 16 | [`055b122`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43048274787) | #218 | 11.11 14:29 | 11.11 15:28 | 0.1 | 2.6 | ✅ |
| 17 | [`6bdcbe3`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43028461464) | #207 | 11.11 12:18 | 11.11 13:24 | < 0.1 | 2.0 | ✅ |
| 18 | [`235bfe6`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43028002822) | #214 | 11.11 12:35 | 11.11 13:21 | < 0.1 | 2.5 | ✅ |
| 19 | [`db781a5`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43027619962) | #217 | 11.11 13:04 | 11.11 13:18 | 0.1 | 2.1 | ✅ |
| 20 | [`a64e06c`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43027083122) | #216 | 11.11 13:04 | 11.11 13:15 | < 0.1 | 2.1 | ✅ |
| 21 | [`90bf687`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43026379163) | #215 | 11.11 12:58 | 11.11 13:10 | < 0.1 | 2.6 | ✅ |
| 22 | [`e238007`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43025694201) | #213 | 11.11 12:58 | 11.11 13:05 | < 0.1 | 2.0 | ✅ |
| 23 | [`e9023b6`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43025179511) | #212 | 11.11 12:58 | 11.11 13:02 | < 0.1 | 2.1 | ✅ |
| 24 | [`4ab84fd`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43024688394) | #211 | 11.11 12:51 | 11.11 12:58 | 0.1 | 1.6 | ✅ |
| 25 | [`d1a42d5`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43024227359) | #210 | 11.11 12:35 | 11.11 12:55 | < 0.1 | 2.5 | ✅ |
| 26 | [`6996961`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43023708038) | #209 | 11.11 12:35 | 11.11 12:51 | < 0.1 | 1.5 | ✅ |
| 27 | [`26adcc7`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43022947278) | #208 | 11.11 12:34 | 11.11 12:46 | 0.1 | 2.0 | ✅ |
| 28 | [`2fe147a`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43018712277) | #206 | 11.11 11:21 | 11.11 12:17 | 0.1 | 2.1 | ✅ |
| 29 | [`f8f1ddb`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43008429534) | #205 | 06.11 12:09 | 11.11 11:02 | 0.1 | 1.6 | ✅ |
| 30 | [`e6d3fc0`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42388071536) | #203 | 06.11 00:37 | 07.11 15:49 | 0.1 | 1.6 | ✅ |
| 31 | [`b70eaa1`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42134284359) | #202 | 05.11 23:39 | 06.11 00:08 | 0.1 | 2.3 | ✅ |
| 32 | [`c15527b`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42133839252) | #201 | 05.11 23:17 | 06.11 00:04 | < 0.1 | 2.5 | ✅ |
| 33 | [`40ea154`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42126056105) | #200 | 05.11 22:55 | 05.11 23:01 | < 0.1 | 2.0 | ✅ |
| 34 | [`8f8e374`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42121525184) | #199 | 05.11 22:22 | 05.11 22:28 | < 0.1 | 1.9 | ✅ |
| 35 | [`65accd6`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42118815381) | #198 | 05.11 21:46 | 05.11 22:09 | 0.1 | 1.6 | ✅ |
| 36 | [`574d497`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42112798859) | #197 | 05.11 21:14 | 05.11 21:29 | < 0.1 | 1.8 | ✅ |
| 37 | [`63ac54d`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42109114025) | #196 | 05.11 20:59 | 05.11 21:05 | 0.1 | 1.6 | ✅ |
| 38 | [`f6eb59c`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42108056676) | #195 | 05.11 20:53 | 05.11 20:58 | < 0.1 | 2.0 | ✅ |
| 39 | [`6c5054d`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42023826618) | #194 | 05.11 12:00 | 05.11 12:04 | < 0.1 | 1.9 | ✅ |
| 40 | [`ff2b2cf`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42020293188) | #193 | 05.11 11:31 | 05.11 11:38 | 0.1 | 2.1 | ✅ |
| 41 | [`ed457e1`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42018445483) | #192 | 05.11 11:17 | 05.11 11:24 | < 0.1 | 1.8 | ✅ |
| 42 | [`00a21dd`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42016189087) | #191 | 05.11 11:02 | 05.11 11:08 | 0.1 | 2.1 | ✅ |
| 43 | [`4b5cf14`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/42007575020) | — | 05.11 12:03 | 05.11 10:06 | 0.1 | 2.0 | ✅ |
| 44 | [`6b6ea30`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41949225715) | #189 | 05.11 01:29 | 05.11 01:34 | 0.1 | 1.8 | ✅ |
| 45 | [`9ce1912`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41946494915) | #188 | 05.11 00:53 | 05.11 01:11 | < 0.1 | 2.0 | ✅ |
| 46 | [`67eef34`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41943188375) | #187 | 05.11 00:38 | 05.11 00:43 | < 0.1 | 1.6 | ✅ |
| 47 | [`4bd1af8`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41940796405) | #186 | 05.11 00:17 | 05.11 00:23 | < 0.1 | 1.8 | ✅ |
| 48 | [`8a9441d`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41934087487) | #184 | 04.11 23:15 | 04.11 23:30 | 0.1 | 1.5 | ✅ |
| 49 | [`8038e3d`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41933441871) | #183 | 04.11 23:02 | 04.11 23:26 | < 0.1 | 1.7 | ✅ |
| 50 | [`5c42560`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41932702215) | #185 | 04.11 23:15 | 04.11 23:19 | < 0.1 | 1.1 | ✅ |
| 51 | [`640dd14`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41927072910) | #182 | 04.11 22:29 | 04.11 22:39 | 0.1 | 1.2 | ✅ |
| 52 | [`165483e`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41924217701) | #181 | 04.11 21:54 | 04.11 22:20 | < 0.1 | 1.4 | ✅ |
| 53 | [`af7757a`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41913957642) | #180 | 04.11 20:53 | 04.11 21:14 | < 0.1 | 1.4 | ✅ |
| 54 | [`c90a5e7`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41906199619) | #179 | 04.11 19:42 | 04.11 20:25 | 0.1 | 1.3 | ✅ |
| 55 | [`2b8e6fa`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41904682681) | #178 | 04.11 20:09 | 04.11 20:15 | 0.1 | 1.4 | ✅ |
| 56 | [`bd23fe7`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41895308930) | #177 | 04.11 19:04 | 04.11 19:17 | < 0.1 | 1.5 | ✅ |
| 57 | [`4b5774b`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41882907847) | #176 | 04.11 17:26 | 04.11 18:02 | 0.1 | 0.9 | ✅ |
| 58 | [`e34316e`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41881985624) | #175 | 04.11 17:16 | 04.11 17:57 | 0.1 | 1.2 | ✅ |
| 59 | [`057e63e`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41873943327) | #174 | 04.11 16:59 | 04.11 17:05 | < 0.1 | 1.3 | ✅ |
| 60 | [`5d009c7`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41868835802) | #173 | 04.11 16:10 | 04.11 16:37 | 0.1 | 1.4 | ✅ |
| 61 | [`67de775`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41862071221) | #171 | 04.11 15:10 | 04.11 15:53 | 0.1 | 1.4 | ✅ |
| 62 | [`0b9bedd`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41848550394) | #170 | 04.11 14:26 | 04.11 14:33 | 0.1 | 1.0 | ✅ |
| 63 | [`1834a79`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41847509958) | #169 | 04.11 14:12 | 04.11 14:27 | 0.1 | 1.3 | ✅ |
| 64 | [`13e3fea`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41847223276) | #168 | 04.11 14:12 | 04.11 14:25 | < 0.1 | 1.0 | ✅ |
| 65 | [`3456429`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41846865163) | — | 04.11 16:22 | 04.11 14:23 | 0.1 | 0.8 | ✅ |
| 66 | [`ab7a9a0`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41846510590) | #153 | 01.11 23:33 | 04.11 14:21 | < 0.1 | 1.2 | ✅ |
| 67 | [`92a3df7`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41845080177) | #166 | 04.11 14:02 | 04.11 14:12 | 0.1 | 0.8 | ✅ |
| 68 | [`4893f9c`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41842600188) | #156 | 04.11 12:35 | 04.11 13:56 | 0.1 | 1.0 | ✅ |
| 69 | [`5925827`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41842197703) | #162 | 04.11 13:43 | 04.11 13:54 | 0.1 | 1.1 | ✅ |
| 70 | [`edd3315`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41841763847) | #163 | 04.11 12:35 | 04.11 13:51 | 0.1 | 1.2 | ✅ |
| 71 | [`c3e2110`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41841476042) | #160 | 04.11 12:35 | 04.11 13:49 | < 0.1 | 1.2 | ✅ |
| 72 | [`26c2d8b`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41840964961) | #161 | 04.11 12:35 | 04.11 13:46 | 0.1 | 1.0 | ✅ |
| 73 | [`76c6244`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41840446655) | #165 | 04.11 12:36 | 04.11 13:43 | 0.1 | 1.2 | ✅ |
| 74 | [`40729b3`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41840094954) | #159 | 04.11 12:35 | 04.11 13:40 | 0.1 | 1.2 | ✅ |
| 75 | [`67090d2`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41839648848) | #158 | 04.11 12:48 | 04.11 13:37 | 0.1 | 1.0 | ✅ |
| 76 | [`2c7c62a`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41839074449) | #155 | 04.11 12:48 | 04.11 13:34 | < 0.1 | 1.2 | ✅ |
| 77 | [`6a2a227`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41834657856) | #152 | 01.11 23:23 | 04.11 13:04 | < 0.1 | 1.0 | ✅ |
| 78 | [`92506f4`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41832180394) | #151 | 01.11 23:18 | 04.11 12:47 | 0.1 | 0.8 | ✅ |
| 79 | [`2eea2ed`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41831390470) | #150 | 01.11 23:11 | 04.11 12:42 | 0.1 | 1.2 | ✅ |
| 80 | [`6d4c1eb`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41830738635) | #149 | 01.11 23:06 | 04.11 12:37 | < 0.1 | 1.1 | ✅ |
| 81 | [`b9ab085`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41354828785) | #148 | 01.11 20:51 | 01.11 22:00 | 0.1 | 0.8 | ✅ |
| 82 | [`43caa7f`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41353392228) | #147 | 01.11 21:40 | 01.11 21:43 | 0.1 | 1.1 | ✅ |
| 83 | [`643b2ba`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41352108126) | #146 | 01.11 21:14 | 01.11 21:28 | < 0.1 | 1.1 | ✅ |
| 84 | [`5d3e5cd`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41351876121) | #145 | 01.11 20:53 | 01.11 21:26 | 0.1 | 1.1 | ✅ |
| 85 | [`dd79967`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41351401583) | #144 | 01.11 20:46 | 01.11 21:20 | 0.1 | 1.1 | ✅ |
| 86 | [`875fed4`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41351093100) | #143 | 01.11 20:39 | 01.11 21:16 | < 0.1 | 1.0 | ✅ |
| 87 | [`047ba55`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41344754912) | #142 | 01.11 19:39 | 01.11 20:02 | 0.1 | 0.7 | ✅ |
| 88 | [`06c1690`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41343166280) | #141 | 01.11 19:22 | 01.11 19:44 | < 0.1 | 0.9 | ✅ |
| 89 | [`c8101b7`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41340546004) | #140 | 01.11 18:43 | 01.11 19:13 | < 0.1 | 0.7 | ✅ |
| 90 | [`9700fd2`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41338608738) | #139 | 01.11 18:30 | 01.11 18:50 | 0.1 | 0.6 | ✅ |
| 91 | [`daae23a`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41335692213) | #138 | 01.11 17:16 | 01.11 18:16 | < 0.1 | 0.4 | ✅ |
| 92 | [`dd8227f`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41332841670) | #137 | 01.11 17:06 | 01.11 17:43 | 0.9 | 0.3 | ✅ |
| 93 | [`9e412c8`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41329199828) | #133 | 01.11 14:54 | 01.11 17:00 | 0.1 | 0.3 | ✅ |
| 94 | [`dae41f4`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41326924917) | #128 | 01.11 15:45 | 01.11 16:33 | 0.1 | 0.3 | ✅ |
| 95 | [`ffaefb7`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41325487860) | #127 | 01.11 15:29 | 01.11 16:17 | 0.1 | 0.4 | ✅ |
| 96 | [`adead61`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41317497642) | #126 | 01.11 14:19 | 01.11 14:42 | < 0.1 | 0.2 | ✅ |
| 97 | [`c43727d`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41312694535) | #125 | 01.11 03:22 | 01.11 13:44 | 0.1 | 0.4 | ✅ |
| 98 | [`fbdb45d`](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/41298858670) | #123 | 31.10 14:25 | 01.11 10:45 | < 0.1 | 0.3 | ✅ |

## 3. Зведена статистика вибірки (01.11 – 13.11.2026)

- **Загальна кількість запусків на main**: 98
- **Успішних запусків (зелених)**: 98 (100%)
- **Невдалих запусків (червоних)**: 0 (0%)
- **Час у черзі (Queue time)**: медіана = **0.00 хв** (< 0.1 хв), середнє = **0.06 хв**, максимум = **0.90 хв** (01.11 перед дедлайном)
- **Час виконання (Execution time)**: медіана = **1.50 хв**, середнє = **1.53 хв**, діапазон = **0.2 – 2.9 хв**
- **Час виконання змін (Change Lead Time)**:
  - Медіана: **21.4 хв (0.36 год)**
  - Середнє: **335.0 хв (5.58 год)**
  - Розподіл: **77** запусків (78.6%) мали lead time **< 1 години**.

### Розподіл запусків за днями:

| Дата | Кількість запусків CI на main | Характер активності |
|:---:|:---:|---|
| 13.11 | 3 | Поточні доопрацювання та документація |
| 12.11 | 9 | Релізи v1.0.0, v1.0.1, v1.0.2 |
| 11.11 | 17 | Оновлення залежностей Dependabot та Lab 9 |
| 07.11 | 1 | Поточні доопрацювання та документація |
| 06.11 | 2 | Поточні доопрацювання та документація |
| 05.11 | 15 | Доопрацювання надійності та автодеплою |
| 04.11 | 33 | Активна розробка каталогу та рев'ю (33 злиття) |
| 01.11 | 18 | Дедлайн (Midterm / Labs 3-7) — масові злиття PR |

## 4. Висновки Етапу 1 для розрахунку DORA (Етап 2)

1. **Черга (Queue Time)**: оскільки конвеєр налаштовано на runner `ubuntu-latest`, запуски стартують миттєво. Навіть 1 листопада під час загального навантаження максимальна черга склала лише 0.9 хв (54 сек), а медіана залишалася практично нульовою (< 6 секунд).
2. **Швидкість виконання (Execution Time)**: медіана 1.5 хв демонструє високу ефективність кешування pip/npm та оптимізацію кроків збірки (орієнтир CircleCI — до 10 хв, індустріальна медіана 2025 р. — 2.2 хв).
3. **Стабільність (Change Fail Rate)**: 0% червоних запусків на `main`. Вся фільтрація помилок (flaky/broken tests, linter failures) здійснюється на рівні PR перед злиттям.
4. **Час доставки змін (Lead Time)**: понад 78% усіх змін доходять від першого коміту в гілці до завершення розгортання менше ніж за 1 годину (медіана 21.4 хв).
