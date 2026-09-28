import json
import os

def transform_dataset(input_file, output_folder):
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created directory: {output_folder}")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find input file at {input_file}")
        return

    # Process lines in steps of 2 (neighbored pairs)
    pair_count = 0
    
    for i in range(0, len(lines), 2):
        if i + 1 >= len(lines):
            break
            
        entry_a = json.loads(lines[i])
        entry_b = json.loads(lines[i+1])

        # # Verify they belong to the same patch/commit
        # match_keys = ["project", "commit_id", "project_url", "commit_url", "commit_message"]
        # is_match = all(entry_a.get(k) == entry_b.get(k) for k in match_keys)
        
        # if not is_match:
        #     print(f"Warning: Entries at line {i+1} and {i+2} do not match metadata. Skipping.")
        #     continue

        # Identify which is before (target=1) and which is after (target=0)
        before = None
        after = None
        
        if entry_a['target'] == 1 and entry_b['target'] == 0:
            before, after = entry_a, entry_b
        elif entry_b['target'] == 1 and entry_a['target'] == 0:
            before, after = entry_b, entry_a
        else:
            print(f"Warning: Lines {i+1}-{i+2} are not a 1/0 target pair. Skipping.")
            continue

        # Prepare the LLM4Vuln structure
        # Use the CVE field if available, otherwise fallback to idx for filename
        cve_id = before.get("cve")
        if not cve_id or str(cve_id).lower() == "none":
            filename = f"UNKNOWN_{before['idx']}.json"
        else:
            filename = f"{cve_id}.json"

        output_data = {
            "cve": cve_id,
            "repo_remote": before.get("project_url"),
            "repo_local": "NOT NEEDED",
            "cve_info": before.get("cve_desc"),
            "code_before_patch": {
                "code": before.get("func"),
                "related": []
            },
            "code_after_patch": {
                "code": after.get("func"),
                "related": []
            }
        }

        # Write the individual JSON file
        output_path = os.path.join(output_folder, filename)
        with open(output_path, 'w', encoding='utf-8') as out_f:
            json.dump(output_data, out_f, indent=4)
        
        pair_count += 1

    print(f"Successfully transformed {pair_count} pairs into {output_folder}")

if __name__ == "__main__":
    # Define paths
    INPUT_JSONL = "primevul_test_paired.jsonl"
    OUTPUT_DIR = "cpp_primevul"

    transform_dataset(INPUT_JSONL, OUTPUT_DIR)





# LLM4Vuln structure, example: dataset/cpp/CVE-2011-1943.json
""" {
    "cve": "CVE-2011-1943",
    "repo_remote": "https://cgit.freedesktop.org/NetworkManager/NetworkManager/commit/?id=78ce088843d59d4494965bfc40b30a2e63d065f6",
    "repo_local": "NOT NEEDED",
    "cve_info": "The destroy_one_secret function in nm-setting-vpn.c in libnm-util in the NetworkManager package 0.8.999-3.git20110526 in Fedora 15 creates a log entry containing a certificate password, which allows local users to obtain sensitive information by reading a log file.",
    "code_before_patch": {
        "code": "destroy_one_secret (gpointer data)\n{\n \tchar *secret = (char *) data;\n \n \t/* Don't leave the secret lying around in memory */\ng_message (\"%s: destroying %s\", __func__, secret);\n \tmemset (secret, 0, strlen (secret));\n \tg_free (secret);\n }\n",
        "related": [
            "static void\nnm_setting_vpn_init (NMSettingVPN *setting)\n{\n\tNMSettingVPNPrivate *priv = NM_SETTING_VPN_GET_PRIVATE (setting);\n\tg_object_set (setting, NM_SETTING_NAME, NM_SETTING_VPN_SETTING_NAME, NULL);\n\tpriv->data = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, g_free);\n\tpriv->secrets = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, destroy_one_secret);\n}\n"
        ]
    },
    "code_after_patch": {
        "code": "destroy_one_secret (gpointer data)\n{\n \tchar *secret = (char *) data;\n \n \t/* Don't leave the secret lying around in memory */\n \tmemset (secret, 0, strlen (secret));\n \tg_free (secret);\n }\n",
        "related": [
            "static void\nnm_setting_vpn_init (NMSettingVPN *setting)\n{\n\tNMSettingVPNPrivate *priv = NM_SETTING_VPN_GET_PRIVATE (setting);\n\tg_object_set (setting, NM_SETTING_NAME, NM_SETTING_VPN_SETTING_NAME, NULL);\n\tpriv->data = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, g_free);\n\tpriv->secrets = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, destroy_one_secret);\n}\n"
        ]
    }
} """

# PrimeVul_paired structure: 1 entry with target = 0, one with target = 1; same "project", "commit_id", "project_url", "commit_url", and "commit_message" (use for matching)
## Mapping to work with LLM4Vuln
# cve -> cve
# repo_remote -> project_url
# repo_local -> "NOT NEEDED"
# cve_info -> cve_desc
# code_before_patch
#   code -> func (target = 1)
#   related: leave empty []
# code_after_patch
#   code -> func (target = 0)
#   related: leave empty []
## each example must be in its own .json file
""" {
    "idx": 195017, 
    "project": "gpac", 
    "commit_id": "ad18ece95fa064efc0995c4ab2c985f77fb166ec", 
    "project_url": "https://github.com/gpac/gpac", 
    "commit_url": "https://github.com/gpac/gpac/commit/ad18ece95fa064efc0995c4ab2c985f77fb166ec", 
    "commit_message": "fixed #1904", 
    "target": 1, 
    "func": "u32 GetHintFormat(GF_TrackBox *trak)\n{\n\tGF_HintMediaHeaderBox *hmhd = (GF_HintMediaHeaderBox *)trak->Media->information->InfoHeader;\n\tif (hmhd->type != GF_ISOM_BOX_TYPE_HMHD)\n\t\treturn 0;\n\t\t\n\tif (!hmhd || !hmhd->subType) {\n\t\tGF_Box *a = (GF_Box *)gf_list_get(trak->Media->information->sampleTable->SampleDescription->child_boxes, 0);\n\t\tif (!hmhd) return a ? a->type : 0;\n\t\tif (a) hmhd->subType = a->type;\n\t\treturn hmhd->subType;\n\t}\n\treturn hmhd->subType;\n}", 
    "func_hash": 91218268849686441388880855658517990203, 
    "file_name": "hint_track.c", 
    "file_hash": 60176895274654779679144452624639678766, 
    "cwe": ["CWE-476"], 
    "cve": "CVE-2021-40576", 
    "cve_desc": "The binary MP4Box in Gpac 1.0.1 has a null pointer dereference vulnerability in the gf_isom_get_payt_count function in hint_track.c, which allows attackers to cause a denial of service.", 
    "nvd_url": https://nvd.nist.gov/vuln/detail/CVE-2021-40576
}"""

