#!/bin/bash
# stress test for slice classification - sends a variety of memories to the api and checks that they get
# classified into the right slices. uses patterns that should trigger specific rules plus some ambiguous
# ones that rely on embedding similarity. logs each result so you can eyeball the classification quality.
# run with: chmod +x scripts/stress-test-slices.sh && ./scripts/stress-test-slices.sh
# -kofi :)

API_KEY="sk_live_0-v0MN3a5LawVA1YusJN9iM_6ZrX16FaBXZCuwaIYTQ"
BASE_URL="${BASE_URL:-http://localhost:3000}"
ENDPOINT="$BASE_URL/api/memories"

echo "=== slice classifier stress test ==="
echo "endpoint: $ENDPOINT"
echo ""

test_memory() {
  local expected_slice="$1"
  local content="$2"
  
  echo "testing: $expected_slice"
  echo "  content: ${content:0:60}..."
  
  response=$(curl -s -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"$content\"}")
  
  if echo "$response" | grep -q "error"; then
    echo "  ❌ error: $response"
    return 1
  fi
  
  echo "  ✓ saved"
  sleep 0.5
}

echo "--- am.attributes (demographics, traits) ---"
test_memory "am.attributes" "I am 28 years old and was born in Seattle."
test_memory "am.attributes" "I have dark brown hair and am about 5'11\"."
test_memory "am.attributes" "I'm generally introverted but become talkative around close friends."
test_memory "am.attributes" "I was diagnosed with ADHD when I was 25."

echo ""
echo "--- am.positions (roles, jobs) ---"
test_memory "am.positions" "I work as a senior software engineer at Anthropic."
test_memory "am.positions" "I'm the tech lead for our infrastructure team."
test_memory "am.positions" "I'm a father of two kids, ages 4 and 7."
test_memory "am.positions" "I co-founded a startup in 2020 focused on developer tools."

echo ""
echo "--- am.competencies (skills, education) ---"
test_memory "am.competencies" "I'm fluent in Python, TypeScript, and Rust."
test_memory "am.competencies" "I have a master's degree in computer science from Stanford."
test_memory "am.competencies" "I speak English natively and conversational Japanese."
test_memory "am.competencies" "I have 8 years of experience building distributed systems."

echo ""
echo "--- do.activities (current work) ---"
test_memory "do.activities" "I'm currently building a memory system for AI assistants."
test_memory "do.activities" "This week I'm focused on implementing the slice classifier."
test_memory "do.activities" "I'm taking an online course on reinforcement learning."
test_memory "do.activities" "I'm reading 'The Staff Engineer's Path' right now."

echo ""
echo "--- do.aims (goals, aspirations) ---"
test_memory "do.aims" "My goal is to become a principal engineer within 3 years."
test_memory "do.aims" "I want to start my own AI research lab someday."
test_memory "do.aims" "I'm trying to publish a paper on memory architectures."
test_memory "do.aims" "By next year I hope to have shipped this product."

echo ""
echo "--- do.situations (challenges, contexts) ---"
test_memory "do.situations" "I'm dealing with burnout from the last few months."
test_memory "do.situations" "I'm in the process of switching teams within the company."
test_memory "do.situations" "I just moved to a new city and am still settling in."
test_memory "do.situations" "I'm facing a tough decision about going back to school."

echo ""
echo "--- think.preferences (likes, dislikes) ---"
test_memory "think.preferences" "I prefer working async over having lots of meetings."
test_memory "think.preferences" "I love dark mode for everything - can't stand light themes."
test_memory "think.preferences" "I'm a morning person and do my best work before noon."
test_memory "think.preferences" "I prefer strongly typed languages over dynamic ones."

echo ""
echo "--- think.principles (values, beliefs) ---"
test_memory "think.principles" "I believe in shipping fast and iterating based on feedback."
test_memory "think.principles" "I value transparency and directness in communication."
test_memory "think.principles" "It's important to me that my work has positive impact."
test_memory "think.principles" "My philosophy is that simple solutions beat clever ones."

echo ""
echo "--- think.patterns (habits, tendencies) ---"
test_memory "think.patterns" "I tend to overthink decisions before committing."
test_memory "think.patterns" "I always write tests after getting the core logic working."
test_memory "think.patterns" "When I'm stressed, I usually go for a long walk."
test_memory "think.patterns" "I'm the type of person who makes lists for everything."

echo ""
echo "--- ambiguous cases (embedding-based) ---"
test_memory "?" "Building ml pipelines in python with pytorch and huggingface."
test_memory "?" "Had a productive conversation with the team about roadmap."
test_memory "?" "The deployment went smoothly after fixing the config issue."
test_memory "?" "Need to follow up with Sarah about the design review."

echo ""
echo "=== stress test complete ==="
echo "check the memories in supabase to verify slice assignments!"

