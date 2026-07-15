# Whole-System Decision-Support Demo OutputClinical framing: decision-support only, not autonomous diagnosis.Image: `/content/drive/MyDrive/plm_mllm_radiology_demo/input_images/example_cxr.jpg`## Generated FindingsLungs and Airways:
- Diffuse bronchiectasis
- Bronchial wall thickening
- Scattered nodular opacities

Pleura:
- No pleural effusion
- No pneumothorax

Cardiovascular:
- Normal cardiomediastinal silhouette

Musculoskeletal and Chest Wall:
- No acute osseous abnormality## Generated Impression1. Severe bronchiectasis with bronchial wall thickening and cystic changes, consistent with the patient's known history of cystic fibrosis.
2. No evidence of new focal consolidation.
3. Stable cardiomediastinal silhouette.## Case Summary- **case_status**: abnormal_findings_detected- **present_abnormal_findings**: ['Lung Opacity', 'Lung Lesion']- **uncertain_abnormal_findings**: ['Enlarged Cardiomediastinum']- **active_abnormal_findings**: ['Enlarged Cardiomediastinum', 'Lung Opacity', 'Lung Lesion']- **no_finding_state**: not_mentioned## Decision Support- **review_recommended**: True- **review_priority**: medium- **reasons**: ['One or more abnormal findings are extracted as present.', 'One or more abnormal findings are extracted as uncertain.', 'One or more PLM labels have low confidence.', 'One or more active findings belong to high-risk or low-support labels from the 200-case safety analysis.']- **final_note**: This is a decision-support output. It is not a final diagnosis.## Structured Findings```text                     label         state  confidence               source  prob_not_mentioned  prob_absent  prob_uncertain  prob_present  no_finding_rule_applied
                No Finding not_mentioned    0.999206   generated_findings            0.999206     0.000138        0.000091      0.000564                    False
Enlarged Cardiomediastinum     uncertain    0.977945 generated_impression            0.020725     0.000924        0.977945      0.000406                    False
              Cardiomegaly        absent    0.981572   generated_findings            0.016311     0.981572        0.000630      0.001487                    False
              Lung Opacity       present    0.998269 generated_impression            0.001021     0.000401        0.000310      0.998269                    False
               Lung Lesion       present    0.986772   generated_findings            0.004744     0.002704        0.005780      0.986772                    False
                     Edema not_mentioned    0.999428 generated_impression            0.999428     0.000071        0.000113      0.000388                    False
             Consolidation        absent    0.803170 generated_impression            0.000467     0.803170        0.193856      0.002507                    False
                 Pneumonia not_mentioned    0.998581 generated_impression            0.998581     0.000956        0.000214      0.000249                    False
               Atelectasis not_mentioned    0.995299   generated_findings            0.995299     0.000644        0.001541      0.002516                    False
              Pneumothorax        absent    0.993488   generated_findings            0.004311     0.993488        0.001070      0.001130                    False
          Pleural Effusion        absent    0.983240   generated_findings            0.000504     0.983240        0.002406      0.013850                    False
             Pleural Other        absent    0.564533 generated_impression            0.012027     0.564533        0.244487      0.178953                    False
                  Fracture not_mentioned    0.999201 generated_impression            0.999201     0.000523        0.000070      0.000206                    False
           Support Devices not_mentioned    0.997651 generated_impression            0.997651     0.001248        0.000150      0.000951                    False```