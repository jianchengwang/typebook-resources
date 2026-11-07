# English-original children and youth readers

This collection adds complete historical English-original books, not generated
retellings or graded adaptations. The public catalog also keeps the existing
three long-form readers and the separate 100-story children's anthology. Old
single-story IDs remain in the compatibility archive rather than filling the
book picker with one-story entries.

## Selection

The shortlist emphasizes enduring children's and youth literature across fantasy,
family and growing-up stories, adventure, animals, school stories and genuine
multi-story collections. A series volume is a complete independent book; duplicate
editions and separately repackaged parts of the same book are excluded. In particular,
*Little Women* includes both parts and all 47 chapters; *Good Wives* is not listed
again. *Peter Pan* is excluded from this selection because of its special UK rights
position. Modern English translations and the three copyrighted examples mentioned
in the discussion are not silently substituted with unauthorized full text.

Not every historical children's book is easy English. Original vocabulary,
dialects and long sentences can be demanding for learners. Native-reader age
suggestions and content flags are editorial selection aids, not a tested CEFR
rating, a reading-level guarantee or a child-safety certification. Parents and
teachers should review works containing outdated racial/colonial stereotypes,
violence, war, disability language or animal suffering before assigning them.
Text is not silently censored or rewritten.

## Source and rights

Each new book retains its official Project Gutenberg catalog page, full downloaded
HTML, SHA-256 hashes, source URL, original author metadata and a plain-text copy of
the source license. The official page must explicitly say **Public domain in the
USA**. This verifies the source's US designation, not universal public-domain status.
All selected principal authors died in 1946 or earlier; that fact is documented
but does not by itself settle every jurisdiction, contribution or edition.
Check local law before redistribution. Noncommercial educational intent alone is
not treated as permission. No blanket MIT or other replacement license is applied
to these source texts. Source notices and terms remain available with each book.

Chinese and Japanese titles are editorial display labels. They do not imply that
the full text is translated, nor that a particular publisher's translation or
cover has been licensed. Covers are newly generated typographic SVG designs;
source illustrations and publisher cover artwork are not reused as practice assets.

## Data and reproducibility

- `tools/gutenberg_readers.json`: pinned editions, source hashes, selected extraction
  boundaries, expected section/word counts, editorial review and title labels.
- `tools/gutenberg_text.py`: dependency-free HTML extraction with explicit overrides
  for edition-specific section boundaries.
- `tools/import_gutenberg_readers.py`: offline, atomic/recoverable catalog builder.
- `books/pg-*/original.html` and `catalog.html`: original audit sources. They are
  retained in the repository and manifest but omitted from the default practice bundle.
- `books/pg-*/source.json`, `LICENSE.md`, `chapters/*.txt`, `cover.svg`: provenance,
  notices and importable reading material.

The importer does not fetch arbitrary URLs or execute source HTML. New sources
must be obtained and reviewed first, then pinned by hash. To reproduce the current
collection without network access:

```sh
python3 tools/import_gutenberg_readers.py --check
python3 tools/rebuild_prompts.py --check
python3 tools/verify.py
python3 -m unittest discover -s tests -v
```

For an explicitly reviewed update, run the reader importer with `--write`. Its
default is a dry run. Locally changed book payloads, ID collisions, unreviewed
entries, missing source licenses, unexpected files and changed source hashes are
rejected. Source editions remain fixed until intentionally reviewed again.

Reading sections follow the source's actual chapter, story or major section
boundaries. Source-part heading pages, poetry within a story and literary framing
are retained where needed for completeness. A reading section count is therefore
not always identical to a publisher's numbered-chapter count. Extraction omits
navigation, source boilerplate, illustrations and publishing apparatus, not narrative
content. Inspect the per-book extraction diagnostics and reviewed boundaries.

This is a resource-only change. It does not modify TypeBook's importer, update its
pinned resource commit, deploy the website or migrate a user's previously imported
local records. Applications should fetch chapter payloads on demand rather than
preloading the full reading library.

## Reading list

The generated reading list below gives the actual imported counts, not the earlier
candidate count.

Consumers should preserve the source attribution and rights labels and make each
included `LICENSE.md` available when redistributing a book. Keeping these notices
in this repository does not automatically implement notice display in a separate
application importer.

| English title | 中文标题 | 日本語タイトル | Reading sections | Words |
| --- | --- | --- | ---: | ---: |
| [Alice's Adventures in Wonderland](../books/pg-11-alice-s-adventures-in-wonderland/source.json) | 爱丽丝漫游奇境 | 不思議の国のアリス | 12 | 26,441 |
| [Through the Looking-Glass](../books/pg-12-through-the-looking-glass/source.json) | 爱丽丝镜中奇遇 | 鏡の国のアリス | 13 | 29,464 |
| [The Wonderful Wizard of Oz](../books/pg-55-the-wonderful-wizard-of-oz/source.json) | 绿野仙踪 | オズの魔法使い | 24 | 39,272 |
| [The Marvelous Land of Oz](../books/pg-54-the-marvelous-land-of-oz/source.json) | 奥兹国的奇境 | オズの虹の国 | 24 | 41,262 |
| [Ozma of Oz](../books/pg-486-ozma-of-oz/source.json) | 奥兹玛公主 | オズのオズマ姫 | 21 | 38,274 |
| [Dorothy and the Wizard in Oz](../books/pg-420-dorothy-and-the-wizard-in-oz/source.json) | 多萝西与奥兹国大魔法师 | オズの魔法使いとドロシー | 20 | 41,177 |
| [The Road to Oz](../books/pg-485-the-road-to-oz/source.json) | 通往奥兹国的路 | オズへの道 | 24 | 38,834 |
| [The Emerald City of Oz](../books/pg-517-the-emerald-city-of-oz/source.json) | 奥兹国的翡翠城 | オズのエメラルドの都 | 30 | 53,216 |
| [The Patchwork Girl of Oz](../books/pg-955-the-patchwork-girl-of-oz/source.json) | 奥兹国的补丁姑娘 | オズのつぎはぎ娘 | 29 | 57,360 |
| [The Secret Garden](../books/pg-113-the-secret-garden/source.json) | 秘密花园 | 秘密の花園 | 27 | 80,467 |
| [A Little Princess](../books/pg-146-a-little-princess/source.json) | 小公主 | 小公女 | 19 | 66,249 |
| [Little Lord Fauntleroy](../books/pg-479-little-lord-fauntleroy/source.json) | 小公子 | 小公子 | 15 | 58,321 |
| [The Lost Prince](../books/pg-384-the-lost-prince/source.json) | 失踪的王子 | 消えた王子 | 31 | 99,094 |
| [Anne of Green Gables](../books/pg-45-anne-of-green-gables/source.json) | 绿山墙的安妮 | 赤毛のアン | 38 | 102,226 |
| [Anne of Avonlea](../books/pg-47-anne-of-avonlea/source.json) | 少女安妮 | アンの青春 | 30 | 90,847 |
| [Anne of the Island](../books/pg-51-anne-of-the-island/source.json) | 大学时代的安妮 | アンの愛情 | 41 | 76,283 |
| [The Story Girl](../books/pg-5342-the-story-girl/source.json) | 故事姑娘 | ストーリー・ガール | 32 | 87,226 |
| [The Golden Road](../books/pg-316-the-golden-road/source.json) | 金色的道路 | 黄金の道 | 34 | 75,639 |
| [Rainbow Valley](../books/pg-5343-rainbow-valley/source.json) | 彩虹谷 | 虹の谷 | 35 | 80,680 |
| [Emily of New Moon](../books/pg-61236-emily-of-new-moon/source.json) | 新月庄的艾米莉 | 可愛いエミリー | 31 | 113,002 |
| [Rilla of Ingleside](../books/pg-3796-rilla-of-ingleside/source.json) | 壁炉山庄的丽拉 | アンの娘リラ | 35 | 103,178 |
| [Little Women](../books/pg-514-little-women/source.json) | 小妇人 | 若草物語 | 47 | 185,888 |
| [Little Men: Life at Plumfield With Jo's Boys](../books/pg-2788-little-men-life-at-plumfield-with-jo-s-boys/source.json) | 小绅士 | 第三若草物語 | 21 | 104,838 |
| [Jo's Boys](../books/pg-3499-jo-s-boys/source.json) | 乔的男孩们 | 第四若草物語 | 22 | 100,443 |
| [Eight Cousins](../books/pg-2726-eight-cousins/source.json) | 八个表兄弟 | 八人のいとこ | 24 | 72,798 |
| [Rose in Bloom](../books/pg-2804-rose-in-bloom/source.json) | 玫瑰盛开 | 花ざかりのローズ | 22 | 94,097 |
| [An Old-Fashioned Girl](../books/pg-2787-an-old-fashioned-girl/source.json) | 老式女孩 | 昔気質の少女 | 19 | 101,912 |
| [Jack and Jill](../books/pg-2786-jack-and-jill/source.json) | 杰克和吉尔 | ジャックとジル | 24 | 92,756 |
| [Under the Lilacs](../books/pg-3795-under-the-lilacs/source.json) | 紫丁香下 | ライラックの花の下 | 24 | 81,439 |
| [The Railway Children](../books/pg-1874-the-railway-children/source.json) | 铁路边的孩子们 | 鉄道の子どもたち | 14 | 59,268 |
| [Five Children and It](../books/pg-778-five-children-and-it/source.json) | 五个孩子和沙精 | 砂の妖精 | 11 | 53,523 |
| [The Phoenix and the Carpet](../books/pg-836-the-phoenix-and-the-carpet/source.json) | 凤凰与魔毯 | 火の鳥と魔法のじゅうたん | 12 | 61,332 |
| [The Story of the Amulet](../books/pg-837-the-story-of-the-amulet/source.json) | 魔符的故事 | 魔よけ物語 | 14 | 68,418 |
| [The Story of the Treasure Seekers](../books/pg-770-the-story-of-the-treasure-seekers/source.json) | 寻宝的孩子们 | 宝さがしの子どもたち | 16 | 52,449 |
| [The Wouldbegoods: Being the Further Adventures of the Treasure Seekers](../books/pg-794-the-wouldbegoods-being-the-further-adventures-of-the-treasure-seekers/source.json) | 好心办坏事的孩子们 | よい子になろうとした子どもたち | 14 | 78,201 |
| [The Enchanted Castle](../books/pg-3536-the-enchanted-castle/source.json) | 魔法城堡 | 魔法の城 | 12 | 68,293 |
| [The Magic City](../books/pg-20606-the-magic-city/source.json) | 魔法城市 | 魔法の町 | 12 | 58,843 |
| [The House of Arden: A Story for Children](../books/pg-57799-the-house-of-arden-a-story-for-children/source.json) | 阿登府的孩子们 | アーデンの館 | 14 | 72,471 |
| [Harding's luck](../books/pg-28725-harding-s-luck/source.json) | 哈丁的幸运 | ハーディングの幸運 | 12 | 68,423 |
| [Wet Magic](../books/pg-50361-wet-magic/source.json) | 水中的魔法 | 海の魔法 | 12 | 48,892 |
| [The Princess and the Goblin](../books/pg-708-the-princess-and-the-goblin/source.json) | 公主与妖魔 | お姫さまとゴブリンの物語 | 32 | 50,804 |
| [The Princess and Curdie](../books/pg-709-the-princess-and-curdie/source.json) | 公主与柯迪 | カーディとお姫さまの物語 | 35 | 55,883 |
| [At the Back of the North Wind](../books/pg-225-at-the-back-of-the-north-wind/source.json) | 北风的背后 | 北風のうしろの国 | 38 | 88,508 |
| [The Light Princess and Other Fairy Stories](../books/pg-18811-the-light-princess-and-other-fairy-stories/source.json) | 轻飘飘的公主及其他童话 | かるいお姫さまとほかのおとぎ話 | 17 | 32,660 |
| [Black Beauty](../books/pg-271-black-beauty/source.json) | 黑骏马 | 黒馬物語 | 49 | 59,686 |
| [The Jungle Book](../books/pg-236-the-jungle-book/source.json) | 丛林之书 | ジャングル・ブック | 14 | 50,787 |
| [The Second Jungle Book](../books/pg-1937-the-second-jungle-book/source.json) | 第二部丛林之书 | 続ジャングル・ブック | 16 | 63,671 |
| [Just so stories](../books/pg-2781-just-so-stories/source.json) | 原来如此的故事 | なぜなぜ物語 | 12 | 28,710 |
| [Puck of Pook's Hill](../books/pg-557-puck-of-pook-s-hill/source.json) | 普克山的精灵 | プークが丘の妖精パック | 10 | 57,628 |
| [Rewards and Fairies](../books/pg-556-rewards-and-fairies/source.json) | 报酬与精灵 | ごほうびと妖精 | 34 | 72,484 |
| ["Captains Courageous": A Story of the Grand Banks](../books/pg-2186-captains-courageous-a-story-of-the-grand-banks/source.json) | 勇敢的船长 | 勇敢な船長 | 10 | 52,489 |
| [Treasure Island](../books/pg-120-treasure-island/source.json) | 金银岛 | 宝島 | 34 | 67,868 |
| [Kidnapped](../books/pg-421-kidnapped/source.json) | 绑架 | 誘拐されて | 30 | 79,988 |
| [The Black Arrow: A Tale of the Two Roses](../books/pg-848-the-black-arrow-a-tale-of-the-two-roses/source.json) | 黑箭 | 黒い矢 | 33 | 79,285 |
| [The Adventures of Tom Sawyer, Complete](../books/pg-74-the-adventures-of-tom-sawyer-complete/source.json) | 汤姆·索亚历险记 | トム・ソーヤーの冒険 | 35 | 69,817 |
| [The Prince and the Pauper](../books/pg-1837-the-prince-and-the-pauper/source.json) | 王子与贫儿 | 王子と乞食 | 35 | 66,648 |
| [The call of the wild](../books/pg-215-the-call-of-the-wild/source.json) | 野性的呼唤 | 野性の呼び声 | 7 | 31,765 |
| [White Fang](../books/pg-910-white-fang/source.json) | 白牙 | 白い牙 | 25 | 72,030 |
| [Wild Animals I Have Known](../books/pg-3031-wild-animals-i-have-known/source.json) | 我所知道的野生动物 | 私の知る野生動物 | 8 | 50,763 |
| [Animal Heroes](../books/pg-2284-animal-heroes/source.json) | 动物英雄 | 動物の英雄たち | 8 | 55,936 |
| [Bannertail: The Story of a Graysquirrel](../books/pg-42827-bannertail-the-story-of-a-graysquirrel/source.json) | 灰松鼠班纳的故事 | 灰色リスの旗尾 | 37 | 22,000 |
| [Daddy-Long-Legs](../books/pg-157-daddy-long-legs/source.json) | 长腿叔叔 | あしながおじさん | 89 | 36,957 |
| [Pollyanna](../books/pg-1450-pollyanna/source.json) | 波莉安娜 | 少女パレアナ | 32 | 55,517 |
| [Pollyanna Grows Up](../books/pg-6100-pollyanna-grows-up/source.json) | 波莉安娜长大了 | パレアナの青春 | 32 | 73,156 |
| [Just David](../books/pg-440-just-david/source.json) | 少年大卫 | 少年デイヴィッド | 25 | 58,920 |
| [Rebecca of Sunnybrook Farm](../books/pg-498-rebecca-of-sunnybrook-farm/source.json) | 晴溪庄的丽贝卡 | 少女レベッカ | 31 | 73,453 |
| [New Chronicles of Rebecca](../books/pg-1375-new-chronicles-of-rebecca/source.json) | 丽贝卡新传 | レベッカの新しい日々 | 11 | 61,281 |
| [What Katy Did](../books/pg-8994-what-katy-did/source.json) | 凯蒂做了什么 | ケティ物語 | 13 | 49,030 |
| [What Katy Did at School](../books/pg-5141-what-katy-did-at-school/source.json) | 凯蒂在学校 | 学校のケティ | 13 | 51,698 |
| [What Katy Did Next](../books/pg-8995-what-katy-did-next/source.json) | 凯蒂接下来做了什么 | その後のケティ | 11 | 56,349 |
| [Five Little Peppers and How They Grew](../books/pg-2770-five-little-peppers-and-how-they-grew/source.json) | 五个小辣椒的成长 | 五人のペパーきょうだい | 25 | 68,945 |
| [Hans Brinker; Or, The Silver Skates](../books/pg-764-hans-brinker-or-the-silver-skates/source.json) | 汉斯·布林克：银冰鞋 | ハンス・ブリンカー 銀のスケート | 47 | 82,446 |
| [Donald and Dorothy](../books/pg-28856-donald-and-dorothy/source.json) | 唐纳德和多萝西 | ドナルドとドロシー | 35 | 81,243 |
| [Freckles](../books/pg-111-freckles/source.json) | 雀斑男孩 | そばかすの少年 | 20 | 81,555 |
| [A Girl of the Limberlost](../books/pg-125-a-girl-of-the-limberlost/source.json) | 林中女孩 | リンバロストの乙女 | 25 | 119,774 |
| [Glinda of Oz](../books/pg-961-glinda-of-oz/source.json) | 奥兹国的格琳达 | オズのグリンダ | 24 | 39,379 |
| [The Children of the New Forest](../books/pg-6471-the-children-of-the-new-forest/source.json) | 新森林的孩子们 | ニューフォレストの子どもたち | 27 | 113,778 |
| [The Merry Adventures of Robin Hood](../books/pg-964-the-merry-adventures-of-robin-hood/source.json) | 侠盗罗宾汉 | ロビン・フッドの冒険 | 23 | 111,022 |
| [Men of Iron](../books/pg-1557-men-of-iron/source.json) | 铁甲少年 | 鉄の男たち | 35 | 68,070 |
| [Otto of the Silver Hand](../books/pg-2865-otto-of-the-silver-hand/source.json) | 银手奥托 | 銀の手のオットー | 16 | 27,607 |
| [The Story of King Arthur and his Knights](../books/pg-60184-the-story-of-king-arthur-and-his-knights/source.json) | 亚瑟王与圆桌骑士 | アーサー王と騎士たち | 37 | 113,519 |
| [The Story of the Champions of the Round Table](../books/pg-10745-the-story-of-the-champions-of-the-round-table/source.json) | 圆桌勇士的故事 | 円卓の勇士たち | 29 | 123,340 |
| [The Happy Prince, and Other Tales](../books/pg-902-the-happy-prince-and-other-tales/source.json) | 快乐王子及其他故事 | 幸福な王子とほかの物語 | 5 | 16,162 |
| [The Rose and the Ring](../books/pg-897-the-rose-and-the-ring/source.json) | 玫瑰与戒指 | バラと指輪 | 20 | 29,434 |
| [The Little Lame Prince](../books/pg-496-the-little-lame-prince/source.json) | 跛脚小王子 | 足の不自由な小さな王子 | 10 | 27,260 |
| [The Adventures of A Brownie](../books/pg-30494-the-adventures-of-a-brownie/source.json) | 小精灵的冒险 | ブラウニーの冒険 | 6 | 19,676 |
| [The Cuckoo Clock](../books/pg-15569-the-cuckoo-clock/source.json) | 布谷鸟钟 | かっこう時計 | 11 | 36,899 |
| [The Tapestry Room: A Child's Romance](../books/pg-17175-the-tapestry-room-a-child-s-romance/source.json) | 挂毯房间 | タペストリーの部屋 | 12 | 49,177 |
| [The Carved Lions](../books/pg-39549-the-carved-lions/source.json) | 雕刻的狮子 | 木彫りのライオン | 12 | 39,959 |
| [The Slowcoach](../books/pg-2086-the-slowcoach/source.json) | 慢吞吞的马车 | のんびり馬車 | 24 | 52,210 |
| [The Bee-Man of Orn and Other Fanciful Tales](../books/pg-12067-the-bee-man-of-orn-and-other-fanciful-tales/source.json) | 奥恩的养蜂人与其他奇幻故事 | オーンの蜂飼いとほかのふしぎな物語 | 9 | 52,302 |
| [A Jolly Fellowship](../books/pg-20651-a-jolly-fellowship/source.json) | 快乐的伙伴 | 陽気な仲間たち | 25 | 75,042 |
| [Six to Sixteen: A Story for Girls](../books/pg-19360-six-to-sixteen-a-story-for-girls/source.json) | 从六岁到十六岁 | 六歳から十六歳まで | 30 | 63,094 |
| [Jan of the Windmill: A Story of the Plains](../books/pg-5601-jan-of-the-windmill-a-story-of-the-plains/source.json) | 风车旁的扬 | 風車小屋のヤン | 42 | 82,219 |
| [Old-Fashioned Fairy Tales](../books/pg-15592-old-fashioned-fairy-tales/source.json) | 老式童话 | 昔風のおとぎ話 | 19 | 33,255 |
| [The Brownies and Other Tales](../books/pg-16052-the-brownies-and-other-tales/source.json) | 小精灵与其他故事 | ブラウニーとほかの物語 | 6 | 48,134 |

## Verification scope

All 96 source pages declare US public-domain status; source HTML and complete license
footers are retained and pinned. The source chapter/story inventory, narrative openings
and endings, and atypical framing sections were reviewed. Regression tests explicitly
cover the restored prologues, introductory frames, opening poem and complete two-part
*Little Women*. Selected paragraph reconstruction and exact hashes are checked offline.
This is not a claim of line-by-line proofreading against print editions or absence of
all historical transcription errors.

An edition of *Tom Brown’s School Days* was rejected because image-based initial
letters created missing/misattached text; *Glinda of Oz* was selected instead. The
additional translated fairy tales appended to the source volume of *The Little Lame
Prince* are not part of its ten-chapter practice text. The separate poems appended to
*The Adventures of a Brownie* remain in the original source, while the complete
six-Adventure story is the imported work. These exclusions are recorded per book.
