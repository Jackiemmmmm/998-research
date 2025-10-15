# chose this 4 methods to evaluate the performance of the patterns

## Success (success rate) = Whether the question was answered correctly

The first principle of any agentic pattern is correctness.

This dimension measures the effectiveness (effectiveness) of the pattern: Who gets more questions right in the same question bank.

The patterns of assessment are not only about right or wrong, but also involve the completion of tasks.

Some questions are arithmetic → having a unique answer → can be directly calculated for accuracy.

Some questions are JSON planning → determining whether they can meet the schema/constraints → this is more like "task success" rather than "classification accuracy".

Some open-ended questions → the ground truth may not be unique → the determination method is more similar to "successfully completing the task".

## Efficiency (efficiency) = How fast and how cost-effective

The actual deployment focuses on time and cost (latency, steps, tool usage, tokens), especially when there are external tools or long reasoning processes.

This dimension measures practicality/scalability: Under the same accuracy rate, who saves more?

## Robustness (Robustness) = Can the system withstand adverse circumstances?

In reality, there are input noise, tool failures, and retrieval biases.  It makes no sense to claim that something is only effective under ideal conditions.

This dimension measures reliability: how much performance degrades under minor disturbances or tool malfunctions, and whether it can recover on its own.

## Controllability (Controllability) = Whether the output is compliant, interpretable and follows the rules.

Enterprise/security scenarios should be structured, verifiable, and in line with policies;  only when they are controllable can they be launched.

This dimension measures trustworthiness: whether it conforms to the JSON schema, follows the plan, and uses tools according to the whitelist.

## For our evaluate progress, we create 16 dataserts to verify the feasibility of the framework and conduct a preliminary comparison of the performance of the patterns.

```json
{"id":"A1","category":"baseline","prompt":"Compute 17 * 24. Output the number only.","ground_truth":"408","judge":{"mode":"exact"},"robustness":{"perturbations":["Compute 17×24. Output the number only.","What is 17 * 24 ? Number only."]}}
{"id":"A2","category":"baseline","prompt":"Extract JSON {name, price} from: 'The iPhone 15 costs $999.' Return strictly JSON.","ground_truth":{"name":"iPhone 15","price":999},"judge":{"mode":"json"},"schema":{"type":"object","properties":{"name":{"type":"string"},"price":{"type":"number"}},"required":["name","price"]},"robustness":{"perturbations":["Extract {name,price}: 'iphone   15  costs  $ 999 !' (JSON only)","Pull product+price JSON from: iPhone-15 COSTS USD999."]}}
{"id":"A3","category":"baseline","prompt":"Normalize the date '12 October 2025' to ISO 'YYYY-MM-DD'. Output only the date.","ground_truth":"2025-10-12","judge":{"mode":"exact"},"robustness":{"perturbations":["Normalise the date 12 Oct 2025 to YYYY-MM-DD.","Format date: 12th October, 2025 → ISO."]}}
{"id":"A4","category":"baseline","prompt":"What is the capital of France? Output a single word.","ground_truth":null,"judge":{"mode":"regex","pattern":"(?i)^paris$"},"robustness":{"perturbations":["Capital of FRANCE? one word.","What is France's capital city?"]}}
{"id":"B1","category":"reasoning","prompt":"All A are B. All B are C. Are all A C? Answer 'Yes' or 'No' only.","ground_truth":"Yes","judge":{"mode":"exact"},"robustness":{"perturbations":["All A⊆B, all B⊆C. Are all A⊆C? Yes/No.","Given A->B and B->C, conclude for A->C (Yes/No)."]}}
{"id":"B2","category":"reasoning","prompt":"A shop sells 3 apples for $5. How much do 12 apples cost? Output a number in dollars (no symbol).","ground_truth":"20","judge":{"mode":"exact"},"robustness":{"perturbations":["3 apples=$5. Price for 12? Number only.","If 3 cost 5, what is the cost of 12?"]}}
{"id":"B3","category":"reasoning","prompt":"Tom is taller than Jim. Jim is taller than Anna. Who is the shortest? Output the name only.","ground_truth":"Anna","judge":{"mode":"exact"},"robustness":{"perturbations":["Tom>Jim>Anna in height. Shortest?","Ordering: Tom taller than Jim; Jim taller than Anna. Shortest?"]}}
{"id":"B4","category":"reasoning","prompt":"Passage: 'Lena moved from Oslo to Paris in 2022. In 2024, she started a bakery near the Seine. Her sister Mia still lives in Oslo.' Question: In which city did Lena start a bakery? Output the city name only.","ground_truth":"Paris","judge":{"mode":"exact"},"robustness":{"perturbations":["Lena→Paris (2022). In 2024 she opened a bakery by the Seine. Mia remains in Oslo. City of the bakery?","Where did Lena start a bakery? One word."]}}
{"id":"C1","category":"tool","prompt":"Get today's weather in Rome (mocked), and return strictly JSON {temp, condition}.","ground_truth":{"temp":28,"condition":"Sunny"},"judge":{"mode":"json"},"schema":{"type":"object","properties":{"temp":{"type":"number"},"condition":{"type":"string"}},"required":["temp","condition"]},"plan":["weather_api"],"policy":{"tool_whitelist":["weather_api"]},"robustness":{"perturbations":["Rome weather today; JSON {temp,condition} only.","Weather in Rome IT; JSON only."],"tool_failure_prob":0.15}}
{"id":"C2","category":"tool","prompt":"Fetch the mocked USD→EUR rate, then convert 100 USD to EUR. Return JSON {rate, eur}.","ground_truth":{"rate":0.90,"eur":90.0},"judge":{"mode":"json"},"schema":{"type":"object","properties":{"rate":{"type":"number"},"eur":{"type":"number"}},"required":["rate","eur"]},"plan":["fx_api","calculator"],"policy":{"tool_whitelist":["fx_api","calculator"]},"robustness":{"perturbations":["USD to EUR rate (mock). Convert 100 USD. JSON {rate,eur}.","Get fx rate then compute. JSON only."],"tool_failure_prob":0.15}}
{"id":"C3","category":"tool","prompt":"Using the mocked encyclopedia/wikipedia tool, answer: Who discovered penicillin? Return JSON {name, year}.","ground_truth":{"name":"Alexander Fleming","year":1928},"judge":{"mode":"json"},"schema":{"type":"object","properties":{"name":{"type":"string"},"year":{"type":"number"}},"required":["name","year"]},"plan":["wiki_search"],"policy":{"tool_whitelist":["wiki_search"]},"robustness":{"perturbations":["Penicillin discoverer? Return JSON {name,year}.","Use encyclopedia tool; JSON only."],"tool_failure_prob":0.15}}
{"id":"C4","category":"tool","prompt":"Find a mocked USB-C cable under $10 and return JSON {url, price}.","ground_truth":{"url":"https://shop.example/u1","price":9.5},"judge":{"mode":"json"},"schema":{"type":"object","properties":{"url":{"type":"string"},"price":{"type":"number"}},"required":["url","price"]},"plan":["shopping_search"],"policy":{"tool_whitelist":["shopping_search"]},"robustness":{"perturbations":["Find USB-C cable < $10. JSON {url,price}.","USB-C cable cheap; JSON only."],"tool_failure_prob":0.15}}
{"id":"D1","category":"planning","prompt":"Measure exactly 4L using only a 3L and a 5L jug. Describe the steps briefly, ending with the final state.","ground_truth":null,"judge":{"mode":"regex","pattern":"(?i)\\b4\\s*L\\b"},"robustness":{"perturbations":["Use 3L & 5L jars to obtain 4L. Provide steps.","How to get exactly four litres with 3L/5L?"]}}
{"id":"D2","category":"planning","prompt":"Plan a 2-day Rome itinerary including at least three attractions: Colosseum, Trevi Fountain, Vatican Museums. Return JSON {day1:[...], day2:[...]}.","ground_truth":null,"judge":{"mode":"regex","pattern":"(?s).*Colosseum.*(?s).*Trevi Fountain.*(?s).*Vatican Museums.*"},"schema":{"type":"object","properties":{"day1":{"type":"array","items":{"type":"string"}},"day2":{"type":"array","items":{"type":"string"}}},"required":["day1","day2"]},"robustness":{"perturbations":["2-day Rome plan incl. Colosseum, Trevi Fountain, Vatican Museums. JSON only.","Rome itinerary (2 days). Include the three named sites. JSON {day1,day2}."]}}
{"id":"D3","category":"planning","prompt":"Grid path (5x5). S=start at (1,1); G=goal at (5,5); X=blocked. Grid rows:\\nS . . X .\\n. X . . .\\n. . X . .\\n. . . . X\\n. X . . G\\nReturn JSON {path_len, path}, where path is a list of coordinates from start to goal. Use a shortest path.","ground_truth":{"path_len":8},"judge":{"mode":"json","ignore_fields":["path"]},"schema":{"type":"object","properties":{"path_len":{"type":"number"},"path":{"type":"array"}},"required":["path_len","path"]},"robustness":{"perturbations":["Find shortest path in the same grid; JSON {path_len,path}.","Compute minimal steps from (1,1) to (5,5) avoiding X. JSON only."]}}
{"id":"D4","category":"planning","prompt":"Given availability (30-min slots):\\nA: 2025-09-22T10:00, 2025-09-22T10:30, 2025-09-22T11:00\\nB: 2025-09-22T10:00, 2025-09-22T11:00\\nC: 2025-09-22T10:00, 2025-09-22T10:30\\nSchedule a 30-min meeting for A,B,C. Return JSON {start, end, attendees} with attendees sorted alphabetically.","ground_truth":{"start":"2025-09-22T10:00","end":"2025-09-22T10:30","attendees":["A","B","C"]},"judge":{"mode":"json"},"schema":{"type":"object","properties":{"start":{"type":"string"},"end":{"type":"string"},"attendees":{"type":"array","items":{"type":"string"}}},"required":["start","end","attendees"]},"robustness":{"perturbations":["Same availabilities; schedule meeting JSON {start,end,attendees}.","Find common 30-min slot for A/B/C; JSON only."]}}

```

Category A: Basic tasks (arithmetic, simple questions and answers) to measure Success

Category B: Requires tools/external information

Measure Efficiency + Controllability

Category C: Simulation of disturbances and failures

Measure Robustness

CategoryD: Open tasks (planning, JSON output)

Measure Controllability