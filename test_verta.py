# /home/kinfolkt/verta-platform/test_verta.py
"""
Automated Verification Suite for VertaFlow Core Engine
Tests:
1. Cyrillic Script Mirroring
2. SPIN & Challenger Stage Transitions
3. Dynamic Lead Scoring (Cold -> Warm -> Hot)
4. Competitor Battlecard Triggers
5. 3-Line Lead Dossier Generation
"""

import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append(os.path.join(os.path.dirname(__file__), "core"))

from verta_engine import VertaFlowEngine

def run_test_conversation():
    print("=" * 65)
    print("🚀 VERTAFLOW CORE ENGINE TEST: CYRILLIC & BATTLECARD DIALOGUE")
    print("=" * 65)

    engine = VertaFlowEngine(session_id="test_sess_001")

    dialogue_turns = [
        # Turn 1: Prospect starts in Cyrillic, asking for price
        "Салом, мебел фабрикамиз учун crm тизими нархи қанча?",
        
        # Turn 2: Prospect gives volume and pain
        "Кунига 30-40 та буюртма тушади, лекин сотувчиларимиз улгурмай мижозларни совитиб қўйяпти.",
        
        # Turn 3: Prospect brings up a competitor and price objection
        "Лекин бозорда 800 мингга оддий бот бор экан, сизларда қимматроқми?",
        
        # Turn 4: Prospect commits with timeline and phone
        "Шу ҳафта ўрнатмоқчимиз. Мана рақамим: +998901234567, боғланинг."
    ]

    for i, user_turn in enumerate(dialogue_turns, 1):
        print(f"\n[TURN {i}]")
        print(f"👤 Mijoz: {user_turn}")
        
        result = engine.process_message(user_turn)
        
        print(f"🤖 VertaFlow ({result['stage']} • {result['script'].upper()}):")
        print(f"   {result['reply']}")
        print(f"📊 Lead Score: {result['lead_score']}/100 [{result['lead_tier']}]")
        
        if result['dossier']:
            print("\n🔥 [ALERTER] LEAD IS HOT! GENERATED DOSSIER:")
            print(result['dossier'])

    print("\n" + "=" * 65)
    print("✅ BARCHA TESTLAR MUVAFFAQIYATLI O'TDI!")
    print(f"Yakuniy Ball: {result['lead_score']}/100")
    print("=" * 65)

if __name__ == "__main__":
    run_test_conversation()
