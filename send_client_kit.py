# -*- coding: utf-8 -*-
"""Kit de livraison client — génère tout le nécessaire pour livrer un client.

Usage :
    python send_client_kit.py <slug_ou_id_ou_nom> [--out DOSSIER] [--open]

Génère (dans ./deliverables/ par défaut) :
    - client_guide.html            → guide interactif (à ouvrir en premier)
    - MaisonNova_<slug>_Client_Kit.zip → dossier client complet
    - ENVOYER_AU_CLIENT.txt        → le texte de l'email à envoyer au client

Aucun secret (mot de passe, clé API) n'est inclus : uniquement l'identifiant,
la clé d'installation et le code public du client.
"""

import argparse
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Kit de livraison client MaisonNova AI")
    parser.add_argument("client", help="Slug, id (agency_XXXXX) ou nom du client")
    parser.add_argument("--out", default="deliverables",
                        help="Dossier de sortie (défaut : ./deliverables)")
    parser.add_argument("--open", action="store_true",
                        help="Ouvre le guide interactif dans le navigateur après génération")
    args = parser.parse_args()

    import clients_store
    import guide_builder
    import widget_code
    import client_kit

    client = clients_store.get_client(args.client)
    if not client:
        print(f"❌ Client introuvable : {args.client!r}")
        print("   Clients disponibles :")
        for cid, cl in clients_store.load_clients().items():
            print(f"   - {cl.get('slug') or cid}  ({ (cl.get('agency') or {}).get('name') or '?' })")
        return 1

    name = (client.get("agency") or {}).get("name") or client.get("slug") or "client"
    slug = client.get("slug") or "client"
    cid = client.get("id") or ""
    install = widget_code.ensure_install(client)

    os.makedirs(args.out, exist_ok=True)

    # 1. Guide interactif
    guide_path = os.path.join(args.out, "client_guide.html")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(guide_builder.build_guide_html(client))
    print(f"✅ Guide interactif : {guide_path}")

    # 2. Dossier client ZIP
    kit_bytes = client_kit.build_kit_zip(client, guide_builder.build_guide_html(client))
    kit_name = client_kit.kit_filename(client)
    kit_path = os.path.join(args.out, kit_name)
    with open(kit_path, "wb") as f:
        f.write(kit_bytes)
    print(f"✅ Dossier client ZIP : {kit_path}")

    # 3. Email d'envoi
    demo_url = widget_code.public_url(client)
    email_path = os.path.join(args.out, "ENVOYER_AU_CLIENT.txt")
    email = (
        f"Objet : 🎉 Votre assistant est prêt, {name} !\n"
        "\n"
        f"Bonjour,\n"
        "\n"
        "Votre assistant de qualification est prêt. Tout est dans votre dossier :\n"
        f"\n"
        f"📎 En pièce jointe : {kit_name}\n"
        "\n"
        "COMMENT FAIRE (3 étapes) :\n"
        "1️⃣ Dézippez le dossier (clic droit → Extraire tout).\n"
        "2️⃣ Double-cliquez sur guide/client_guide.html : le guide interactif s'ouvre\n"
        "   dans votre navigateur et vous accompagne pas à pas.\n"
        "3️⃣ Suivez les étapes pour votre plateforme (WordPress, Wix, Webflow…).\n"
        "   Votre progression est sauvegardée : vous pouvez reprendre plus tard.\n"
        "\n"
        f"🔗 Vous pouvez aussi tester votre assistant tout de suite ici :\n"
        f"{demo_url}\n"
        "\n"
        f"💬 Votre identifiant : {cid} — votre clé est déjà dans le code,\n"
        "   vous n'avez rien à saisir.\n"
        "\n"
        "Bloqué ? Le guide a un bouton « Je suis bloqué » avec les solutions.\n"
        "\n"
        "Bonne mise en ligne !\n"
    )
    with open(email_path, "w", encoding="utf-8") as f:
        f.write(email)
    print(f"✅ Email d'envoi : {email_path}")

    # 4. Récap dans le terminal
    print("\n" + "═" * 62)
    print(f"  {name}")
    print(f"  Identifiant : {cid}  ·  Clé : {install.get('key') or '—'}")
    print("═" * 62)
    print(f"  🔗 Lien de démo à partager : {demo_url}")
    print(f"  📘 Guide interactif        : {guide_path}")
    print(f"  📦 Dossier client ZIP      : {kit_path}")
    print(f"  ✉️  Email prêt à envoyer    : {email_path}")
    print("═" * 62)

    if args.open:
        import webbrowser
        webbrowser.open("file://" + os.path.abspath(guide_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
