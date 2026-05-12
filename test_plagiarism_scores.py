#!/usr/bin/env python3
"""Test the plagiarism detector with various inputs."""
from detector import PlagiarismDetector

detector = PlagiarismDetector(".")

# Test 1: Exact text from corpus (should be HIGH plagiarism)
test1 = "Technology is changing the modern classroom by improving access to information, digital collaboration, and personalized learning opportunities for students."
result1 = detector.analyze_text(test1)
print("TEST 1 - Exact corpus text:")
print(f"  Plagiarism Score: {result1['plagiarism_score']}%")
print(f"  Risk Level: {result1['risk_level']}")
print(f"  Top Source: {result1['top_sources'][0]['source_text'] if result1['top_sources'] else 'None'}")
print()

# Test 2: Completely new unique text (should be LOW plagiarism)
test2 = "The quick brown fox jumps over lazy dogs in the meadow during sunset hours when the weather is pleasant"
result2 = detector.analyze_text(test2)
print("TEST 2 - Unique new text:")
print(f"  Plagiarism Score: {result2['plagiarism_score']}%")
print(f"  Risk Level: {result2['risk_level']}")
print()

# Test 3: Paraphrased corpus text (should be MODERATE plagiarism)
test3 = "Modern education systems are being transformed by technology, providing better information accessibility, enhanced digital teamwork, and customized educational strategies for learners."
result3 = detector.analyze_text(test3)
print("TEST 3 - Paraphrased corpus text:")
print(f"  Plagiarism Score: {result3['plagiarism_score']}%")
print(f"  Risk Level: {result3['risk_level']}")
print(f"  Top Source: {result3['top_sources'][0]['source_text'] if result3['top_sources'] else 'None'}")
print()

# Test 4: Sample about AI
test4 = "Artificial intelligence is transforming industries by automating routine tasks, examining vast amounts of data, and facilitating smarter decisions."
result4 = detector.analyze_text(test4)
print("TEST 4 - Similar to AI corpus text:")
print(f"  Plagiarism Score: {result4['plagiarism_score']}%")
print(f"  Risk Level: {result4['risk_level']}")
print(f"  Top Source: {result4['top_sources'][0]['source_text'] if result4['top_sources'] else 'None'}")
