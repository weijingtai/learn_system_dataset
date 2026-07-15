import yaml
from pathlib import Path

assertions = []
skipped = []
a_id = 1
p_id = 1

def add_assertion(prop, span_id, conditions, concepts=None, exceptions=None):
    global a_id, p_id
    if concepts is None: concepts = []
    if exceptions is None: exceptions = []
    
    assertions.append({
        'assertion_id': f"as_bazi_{a_id:06d}",
        'proposition': prop,
        'proposition_id': f"pr_bazi_{p_id:06d}",
        'relation': 'supports',
        'evidence': [{
            'source_span_id': span_id,
            'support_type': 'direct'
        }],
        'conditions': conditions,
        'exceptions': exceptions,
        'concept_ids': concepts,
        'status': 'machine_extracted'
    })
    a_id += 1
    p_id += 1

def add_skipped(seg_id, reason):
    skipped.append({
        'seg_id': seg_id,
        'reason': reason
    })

# s01 (p0001_s01)
add_skipped('s01', 'narrative')

# s02 (p0001_s02)
s = 'ss_qtbj_ed01_p0001_s02'
add_assertion("北方阴极而生寒，寒生水", s, [])
add_assertion("南方阳极而生热，热生火", s, [])
add_assertion("东方阳散以泄而生风，风生木", s, [])
add_assertion("西方阴止以收而生燥，燥生金", s, [])
add_assertion("中央阴阳交而生温，温生土", s, [])
add_assertion("五行相生起到相互维系的作用", s, [])
add_assertion("五行相克起到相互制约的作用", s, [])

# s03 (p0001_s03)
s = 'ss_qtbj_ed01_p0001_s03'
add_assertion("火为太阳，性炎上", s, [])
add_assertion("水为太阴，性润下", s, [])
add_assertion("木为少阳，性腾上而无所止", s, [])
add_assertion("金为少阴，性沉下而有所止", s, [])
add_assertion("土无常性，视四时所乘而变化", s, [])
add_assertion("土的作用在于使四时相济得所，不令太过或不及", s, [])

# s04 (p0001_s04)
s = 'ss_qtbj_ed01_p0001_s04'
add_assertion("水的本性主智", s, [])
add_assertion("火的本性主礼", s, [])
add_assertion("木的本性主仁", s, [])
add_assertion("金的本性主义", s, [])
add_assertion("土的本性主信，重宽厚博大，无所不容", s, [])
add_assertion("水附土而行", s, [])
add_assertion("木托土而生", s, [])
add_assertion("金不得土则无自出", s, [])
add_assertion("火不得土则无自归", s, [])
add_assertion("五行皆依赖土", s, [])

# s05 (p0001_s05)
s = 'ss_qtbj_ed01_p0001_s05'
add_assertion("水的正色为黑", s, [])
add_assertion("火的正色为赤", s, [])
add_assertion("木的正色为青", s, [])
add_assertion("土的正色为黄", s, [])
add_assertion("五行表现为其正色", s, ["生旺时"])
add_assertion("五行表现为其母色", s, ["死绝时"])
add_assertion("五行表现为其妻色", s, ["成形冠带时"])
add_assertion("五行表现为其鬼色", s, ["病败时"])
add_assertion("五行表现为其子色", s, ["旺墓时"])

# s06 (p0001_s06)
s = 'ss_qtbj_ed01_p0001_s06'
add_assertion("水的数为一", s, [])
add_assertion("火的数为二", s, [])
add_assertion("木的数为三", s, [])
add_assertion("金的数为四", s, [])
add_assertion("土的数为五", s, [])
add_assertion("五行之数加倍", s, ["生旺时"])
add_assertion("五行之数减半", s, ["死绝时"])

# s07 (p0001_s07)
s = 'ss_qtbj_ed01_p0001_s07'
add_assertion("命理贵在折衷归于中道，使无有余不足之累", s, [])
add_assertion("才官印食贵人驿马等命理微意在于损有余而益不足，归于中道", s, [], ["co_bazi_000004", "co_bazi_000006", "co_bazi_000044", "co_bazi_000007"])
add_assertion("行运同样遵循损有余而补不足的中道原则", s, [])

# p0005_s01
s = 'ss_qtbj_ed01_p0005_s01'
add_assertion("甲木当以火温暖，则有舒畅之美", s, ["春月", "初春犹有余寒"])
add_assertion("甲木若水多则变为克制，有损精神", s, ["春月", "初春犹有余寒"])
add_assertion("甲木必须用庚金斲凿，可成楝梁", s, ["春月", "重见生旺"], ["co_bazi_000035", "co_bazi_000040"])
add_assertion("甲木藉水资扶，则花繁叶茂", s, ["春月", "春末阳壮水渴"])
add_assertion("甲木增之以水，则阴浓气弱，根损枝枯，不能华秀", s, ["春月", "初春", "无火"])
add_assertion("甲木增之以火，则阳气太盛，燥渴相加，枝枯叶干，亦不华秀", s, ["春月", "春末", "失水"])
add_assertion("甲木需水火二物得时相济为美", s, ["春月"], ["co_bazi_000036"])

# p0005_s02
s = 'ss_qtbj_ed01_p0005_s02'
add_assertion("甲木得丙癸同逢，富贵双全", s, ["正月", "初春尚有余寒"])
add_assertion("甲木癸藏丙透，名为寒木向阳，主大富贵，倘风水不及，亦不失儒林俊秀", s, ["正月", "初春尚有余寒"], ["co_bazi_000011"])
add_assertion("甲木如无丙癸，为平常人", s, ["正月", "初春尚有余寒"])

# p0005_s03 (case_candidate: true, exclude cases, extract general rules)
s = 'ss_qtbj_ed01_p0005_s03'
add_assertion("甲木素无取从才、从杀、从化之理", s, ["正二月"], ["co_bazi_000012", "co_bazi_000013", "co_bazi_000014"])
add_assertion("甲木若一派庚辛，主一生劳苦，剋子刑妻", s, ["正二月"])
add_assertion("甲木若一派庚辛，再支会金局，非贫即夭", s, ["正二月"])
add_assertion("甲木若一派壬癸，无丙丁，又无戊己制之，名水泛木浮，死无棺椁", s, ["正二月"], ["co_bazi_000015"])
add_assertion("甲木若一派戊己，支会金局，为财多身弱，富屋贫人，终生劳苦，妻晚子迟", s, ["正二月"], ["co_bazi_000016"])
add_assertion("甲木若无庚金而有丁透，亦属文星，为木火通明之象，又名伤官生财格，主聪明雅秀", s, ["正二月"], ["co_bazi_000017", "co_bazi_000018", "co_bazi_000001"])
add_assertion("甲木若无庚金而有丁透，见癸水伤丁，但作厚道迂儒", s, ["正二月"])
add_assertion("甲木若柱中多癸，滋助木神，伤灭丁火，其人奸雄枭险，言清行浊，笑里藏刀", s, ["正二月"])
add_assertion("甲木若支成金局，多透庚辛，号曰木被金伤，若无丙丁破金，必主残疾", s, ["正二月"], ["co_bazi_000019"])
add_assertion("甲木若支成火局，泄露太过，定主愚懦，常有啾唧灾病缠身，终有暗疾", s, ["正二月"])
add_assertion("甲木若支成木局，得庚为贵", s, ["正二月"])
add_assertion("甲木若支成木局，无庚必凶，若非僧道，男主鳏孤，女主寡独", s, ["正二月"])
add_assertion("甲木若支成水局，戊透为贵", s, ["正二月"])
add_assertion("甲木若支成水局，如无戊制，不但贫贱，且死无棺木", s, ["正二月"])
add_assertion("甲木若无根，全赖申子辰，干得才杀透，平步上青云", s, ["正二月"], ["co_bazi_000003", "co_bazi_000007"])
add_assertion("甲木用庚者，土为妻，金为子", s, ["三春"])
add_assertion("甲木用丁者，木为妻，火为子", s, ["三春"])
add_assertion("甲木有庚戊者为上命", s, ["正二月"])
add_assertion("甲木如有丁透，为大富大贵之命", s, ["正二月"])

# p0005_s04
s = 'ss_qtbj_ed01_p0005_s04'
add_assertion("甲木庚金得所，名阳刃驾杀，可云小贵，异途显达，或主武职，但要财资之", s, ["二月"], ["co_bazi_000020", "co_bazi_000003", "co_bazi_000002"])
add_assertion("甲木柱中逢才，英雄独压万人", s, ["二月", "庚金得所(阳刃驾杀)"], ["co_bazi_000007"])
add_assertion("甲木若见癸水，困了才杀，主为光棍，重刃必定遭凶，性情凶暴", s, ["二月", "庚金得所(阳刃驾杀)"], ["co_bazi_000003", "co_bazi_000007", "co_bazi_000002"])
add_assertion("木旺宜火之光辉，秋闱可试", s, [])
add_assertion("木向春生，处世安然有寿", s, [])
add_assertion("日主无依，却喜运行才地", s, [], ["co_bazi_000007"])

# p0005_s05
s = 'ss_qtbj_ed01_p0005_s05'
add_assertion("甲木木气相竭，先取庚金，次用壬水", s, ["三月"])
add_assertion("甲木庚壬两透，一榜堪图，但要运用相生，风水阴德，方许富贵", s, ["三月"])
add_assertion("甲木或见一二庚金，独取壬水", s, ["三月"])
add_assertion("甲木壬透清秀之人，才学必富", s, ["三月", "见一二庚金"])
add_assertion("甲木天干透出二丙，庚藏支下，此钝斧无钢，富贵难求", s, ["三月"])
add_assertion("甲木天干透出二丙，庚藏支下，若有壬癸破火，堪作秀才", s, ["三月"])
add_assertion("甲木或柱中全无一水，戊己透干，支成土局，作弃命从才，因人而致富贵，妻子有能", s, ["三月"], ["co_bazi_000021", "co_bazi_000007"])
add_assertion("甲木见戊己，及比劫多者，名为杂气夺才，劳碌到老，无驭内之权", s, ["三月"], ["co_bazi_000022", "co_bazi_000009", "co_bazi_000007"])
add_assertion("女命甲木见戊己及比劫多者，女掌男权，贤能内助", s, ["三月", "女命"], ["co_bazi_000009"])
add_assertion("女命甲木见戊己，若比劫重见，淫恶不堪", s, ["三月", "女命"], ["co_bazi_000009"])
add_assertion("甲木支成金局，方可用丁，不然三月无用丁之法，惟有先庚后壬取用", s, ["三月"])
add_assertion("甲乙生寅卯，庚辛干上逢，离南推富贵，坎地却为凶", s, [])

# p0006_s01
s = 'ss_qtbj_ed01_p0006_s01'
add_assertion("甲木退气，丙火司权，先癸后丁", s, ["四月"], ["co_bazi_000041", "co_bazi_000037"])
add_assertion("甲木若庚金太多，甲反受病", s, ["四月"])
add_assertion("甲木若庚金太多，若得壬水方配得中和，此人性好清高，假装富贵，即荫袭显达，终日好作祸乱，善辨巧谈，喜作诗文", s, ["四月"])
add_assertion("甲木如一庚二丙，稍有富贵", s, ["四月"])
add_assertion("甲木金多火多，为下格", s, ["四月"])
add_assertion("甲木癸丁与庚齐透天干，可言科甲，即风水浅薄，亦有选拔之才", s, ["四月"])
add_assertion("甲木癸水不出，虽有庚金丁火，不过富中取贵异途官职而已", s, ["四月"])
add_assertion("甲木壬透可云一富", s, ["四月"])
add_assertion("甲木若全无点水，又无庚金丁火，一派丙戊，此无用之人也", s, ["四月"])

# p0006_s02
s = 'ss_qtbj_ed01_p0006_s02'
add_assertion("甲木先癸后丁，庚金次之", s, ["五月"])
add_assertion("甲木三伏生寒，丁火退气，先丁后庚，无癸亦可", s, ["六月"], ["co_bazi_000041"])
add_assertion("甲木乏癸用丁亦可，要运行北地为佳", s, ["五月"])
add_assertion("甲木用丁火，虽运行北地不致于死，却不利运行火地，号曰木化成灰必死", s, ["五六月"])
add_assertion("甲木用丁火，行西程不吉，号曰伤官遇杀，不测灾来", s, ["五六月"], ["co_bazi_000034", "co_bazi_000001", "co_bazi_000003"])
add_assertion("甲木用丁火，行东方则吉，北方次之", s, ["五六月"])
add_assertion("凡用神太多，不宜剋制，须洩之为妙", s, [], ["co_bazi_000038"])
add_assertion("甲木木盛先庚，庚盛先丁", s, ["五六月"])
add_assertion("甲木癸庚两透，为上上之格", s, ["五月"])
add_assertion("甲木庚丁两透，亦为上上之格", s, ["六月"])
add_assertion("甲木用神既透，木火通明，自然大富大贵", s, ["五六月"], ["co_bazi_000017", "co_bazi_000038"])
add_assertion("甲木或丁火太多，癸水亦多，反作平人", s, ["五六月"])
add_assertion("甲木柱中多金，名曰杀重身轻，先富后贫，运不相扶，非贫即夭", s, ["五六月"], ["co_bazi_000023"])
add_assertion("甲木庚多，有一二丙丁制伏，又有壬癸透干，泄金之气，为先贫后富", s, ["五六月"])
add_assertion("甲木满柱丙火又加丁火，不见官杀，谓之伤官伤尽最为奇，反成清贵，定主才学过人，科甲有望，但岁运不宜见水", s, ["五六月"], ["co_bazi_000024", "co_bazi_000004", "co_bazi_000003"])
add_assertion("甲木满柱丙丁火伤官伤尽，若柱中有壬水，运又逢水，必贫夭死", s, ["五六月"])
add_assertion("凡木火伤官者，聪明智巧，却是人同心异，多见多疑，多抱忌妒之想", s, [], ["co_bazi_000025", "co_bazi_000001"])
add_assertion("女命木火伤官者，聪明智巧，人同心异，多抱忌妒之想", s, ["女命"], ["co_bazi_000025", "co_bazi_000001"])
add_assertion("甲木四柱多土，干上有乙木，切勿作弃命从才", s, ["五六月"], ["co_bazi_000021", "co_bazi_000007"])
add_assertion("甲木时月两透己土，名二土争合，男主奔流，女主淫贱", s, ["五六月"], ["co_bazi_000026"])
add_assertion("甲木时月两透己土，见二甲则不争，亦属平庸之辈", s, ["五六月"])
add_assertion("甲木四柱有辰，干见二己二甲，此人名利双全，大富大贵", s, ["五六月"])
add_assertion("甲木见辰支，名为逢时化合格", s, ["六月"], ["co_bazi_000027"])
add_assertion("甲木化合，以癸水为妻，丁火为子", s, ["六月", "逢时化合"])
add_assertion("甲木若二己一甲争合，取支中比劫为用", s, ["六月"], ["co_bazi_000009"])
add_assertion("甲木以甲为用者，壬癸为妻，甲乙为子", s, ["六月"])
add_assertion("甲木用庚者，土妻金子", s, ["六月"])
add_assertion("甲木用丁者，木妻火子", s, ["六月"])
add_assertion("女命以妻作夫，用作子", s, ["十干皆同", "女命"])
add_assertion("甲木或是己土，不见戊土，乃为假从，其人一生缩首，反畏妻子", s, ["六月"], ["co_bazi_000028"])
add_assertion("甲木假从，若无印绶，一生贫苦", s, ["六月"], ["co_bazi_000028", "co_bazi_000005"])
add_assertion("假从若无印绶一生贫苦，在六月尤可，在五月决不可", s, ["五六月"], ["co_bazi_000028", "co_bazi_000005"])

res = {
    'assertions': assertions,
    'skipped_segments': skipped
}

with open('/Users/jingtaiwei/Git/Public/xuan-migration/learn_system/pipeline/tasks/task_bazi_qtbj_assert_s1/output/draft_gemini.yaml', 'w') as f:
    yaml.dump(res, f, allow_unicode=True, sort_keys=False)

print(f"Total assertions: {len(assertions)}")
print(f"Total skipped: {len(skipped)}")

