/* ============================================================
   SWIFT/BIC 参考辞書（tools/bic のデータ部）
   ------------------------------------------------------------
   ・このファイルだけを編集すれば銀行を追加・修正できます。
   ・キーは先頭8桁のBIC。値は { n:"銀行名", c:"都市" }。
   ・公開情報をもとにした参考用で、網羅的ではありません。
     正式な用途ではSWIFT公式または受取人に確認してください。
   ============================================================ */
/* ===== 主要金融機関 BIC辞書（参考・公開情報ベース／非網羅）。キーは先頭8桁 ===== */
const BANKS = {
// 日本
"BOTKJPJT":{n:"三菱UFJ銀行（MUFG Bank）",c:"東京"},
"SMBCJPJT":{n:"三井住友銀行（SMBC）",c:"東京"},
"MHCBJPJT":{n:"みずほ銀行",c:"東京"},
"SMTCJPJT":{n:"三井住友信託銀行",c:"東京"},
"DIWAJPJT":{n:"りそな銀行",c:"東京"},
// 米国
"CHASUS33":{n:"JPMorgan Chase Bank",c:"ニューヨーク"},
"BOFAUS3N":{n:"Bank of America",c:"ニューヨーク"},
"CITIUS33":{n:"Citibank",c:"ニューヨーク"},
"IRVTUS3N":{n:"The Bank of New York Mellon",c:"ニューヨーク"},
"WFBIUS6S":{n:"Wells Fargo Bank",c:"サンフランシスコ"},
// 英国
"BARCGB22":{n:"Barclays Bank",c:"ロンドン"},
"HBUKGB4B":{n:"HSBC UK Bank",c:"ロンドン"},
"MIDLGB22":{n:"HSBC Bank plc",c:"ロンドン"},
"NWBKGB2L":{n:"NatWest（National Westminster Bank）",c:"ロンドン"},
"LOYDGB2L":{n:"Lloyds Bank",c:"ロンドン"},
// 欧州
"DEUTDEFF":{n:"Deutsche Bank",c:"フランクフルト"},
"COBADEFF":{n:"Commerzbank",c:"フランクフルト"},
"BNPAFRPP":{n:"BNP Paribas",c:"パリ"},
"SOGEFRPP":{n:"Société Générale",c:"パリ"},
"INGBNL2A":{n:"ING Bank",c:"アムステルダム"},
"ABNANL2A":{n:"ABN AMRO Bank",c:"アムステルダム"},
"UBSWCHZH":{n:"UBS",c:"チューリッヒ"},
// 中国
"ICBKCNBJ":{n:"中国工商銀行（ICBC）",c:"北京"},
"BKCHCNBJ":{n:"中国銀行（Bank of China）",c:"北京"},
"ABOCCNBJ":{n:"中国農業銀行（ABC）",c:"北京"},
"PCBCCNBJ":{n:"中国建設銀行（CCB）",c:"北京"},
"COMMCNSH":{n:"交通銀行（Bank of Communications）",c:"上海"},
// 香港
"HSBCHKHH":{n:"香港上海銀行（HSBC）",c:"香港"},
"HASEHKHH":{n:"恒生銀行（Hang Seng Bank）",c:"香港"},
"SCBLHKHH":{n:"Standard Chartered Bank (HK)",c:"香港"},
"BKCHHKHH":{n:"中国銀行（香港）",c:"香港"},
// シンガポール
"DBSSSGSG":{n:"DBS Bank",c:"シンガポール"},
"UOVBSGSG":{n:"United Overseas Bank（UOB）",c:"シンガポール"},
"OCBCSGSG":{n:"OCBC Bank",c:"シンガポール"},
// フィリピン
"BOPIPHMM":{n:"Bank of the Philippine Islands（BPI）",c:"マニラ"},
"MBTCPHMM":{n:"Metrobank（Metropolitan Bank & Trust）",c:"マニラ"},
"BNORPHMM":{n:"BDO Unibank",c:"マニラ"},
"PNBMPHMM":{n:"Philippine National Bank（PNB）",c:"マニラ"},
// ベトナム
"BFTVVNVX":{n:"Vietcombank（ベトナム外商銀行）",c:"ハノイ"},
"ICBVVNVX":{n:"VietinBank",c:"ハノイ"},
"BIDVVNVX":{n:"BIDV（ベトナム投資開発銀行）",c:"ハノイ"},
// インドネシア
"BMRIIDJA":{n:"Bank Mandiri",c:"ジャカルタ"},
"BNINIDJA":{n:"Bank Negara Indonesia（BNI）",c:"ジャカルタ"},
"CENAIDJA":{n:"Bank Central Asia（BCA）",c:"ジャカルタ"},
"BRINIDJA":{n:"Bank Rakyat Indonesia（BRI）",c:"ジャカルタ"},
// タイ
"BKKBTHBK":{n:"Bangkok Bank",c:"バンコク"},
"KASITHBK":{n:"Kasikornbank",c:"バンコク"},
"SICOTHBK":{n:"Siam Commercial Bank（SCB）",c:"バンコク"},
"KRTHTHBK":{n:"Krung Thai Bank",c:"バンコク"},
// インド
"SBININBB":{n:"State Bank of India",c:"ムンバイ"},
"HDFCINBB":{n:"HDFC Bank",c:"ムンバイ"},
"ICICINBB":{n:"ICICI Bank",c:"ムンバイ"},
"AXISINBB":{n:"Axis Bank",c:"ムンバイ"},
// ネパール
"NABLNPKA":{n:"Nabil Bank",c:"カトマンズ"},
// 韓国
"SHBKKRSE":{n:"Shinhan Bank（新韓銀行）",c:"ソウル"},
"CZNBKRSE":{n:"KB Kookmin Bank",c:"ソウル"},
// オーストラリア
"CTBAAU2S":{n:"Commonwealth Bank of Australia",c:"シドニー"},
"NATAAU33":{n:"National Australia Bank（NAB）",c:"メルボルン"},
"WPACAU2S":{n:"Westpac Banking Corporation",c:"シドニー"},
"ANZBAU3M":{n:"ANZ Banking Group",c:"メルボルン"},
// カナダ
"ROYCCAT2":{n:"Royal Bank of Canada（RBC）",c:"トロント"},
"NOSCCATT":{n:"Scotiabank（Bank of Nova Scotia）",c:"トロント"},
"TDOMCATT":{n:"Toronto-Dominion Bank（TD）",c:"トロント"},
// 日本（追加）
"JPPSJPJ1":{n:"ゆうちょ銀行（Japan Post Bank）",c:"東京"},
"LTCBJPJT":{n:"SBI新生銀行",c:"東京"},
"NCBTJPJT":{n:"あおぞら銀行",c:"東京"},
"NOCUJPJT":{n:"農林中央金庫",c:"東京"},
// 米国（追加）
"PNCCUS33":{n:"PNC Bank",c:"ピッツバーグ"},
"USBKUS44":{n:"U.S. Bank",c:"ミネアポリス"},
"SBOSUS33":{n:"State Street Bank and Trust",c:"ボストン"},
"MRMDUS33":{n:"HSBC Bank USA",c:"ニューヨーク"},
// 英国（追加）
"SCBLGB2L":{n:"Standard Chartered Bank",c:"ロンドン"},
"ABBYGB2L":{n:"Santander UK",c:"ロンドン"},
// ドイツ（追加）
"HYVEDEMM":{n:"UniCredit Bank（HypoVereinsbank）",c:"ミュンヘン"},
"GENODEFF":{n:"DZ Bank",c:"フランクフルト"},
// フランス（追加）
"AGRIFRPP":{n:"Crédit Agricole",c:"パリ"},
"CRLYFRPP":{n:"LCL（Le Crédit Lyonnais）",c:"パリ"},
// オランダ（追加）
"RABONL2U":{n:"Rabobank",c:"ユトレヒト"},
// ベルギー
"GEBABEBB":{n:"BNP Paribas Fortis",c:"ブリュッセル"},
"KREDBEBB":{n:"KBC Bank",c:"ブリュッセル"},
// イタリア
"BCITITMM":{n:"Intesa Sanpaolo",c:"ミラノ"},
"UNCRITMM":{n:"UniCredit",c:"ミラノ"},
// スペイン
"BSCHESMM":{n:"Banco Santander",c:"マドリード"},
"BBVAESMM":{n:"BBVA",c:"ビルバオ"},
"CAIXESBB":{n:"CaixaBank",c:"バルセロナ"},
// アイルランド
"BOFIIE2D":{n:"Bank of Ireland",c:"ダブリン"},
"AIBKIE2D":{n:"Allied Irish Banks（AIB）",c:"ダブリン"},
// オーストリア
"BKAUATWW":{n:"UniCredit Bank Austria",c:"ウィーン"},
// スウェーデン
"NDEASESS":{n:"Nordea Bank",c:"ストックホルム"},
"ESSESESS":{n:"SEB（Skandinaviska Enskilda Banken）",c:"ストックホルム"},
"HANDSESS":{n:"Svenska Handelsbanken",c:"ストックホルム"},
// デンマーク
"DABADKKK":{n:"Danske Bank",c:"コペンハーゲン"},
// ノルウェー
"DNBANOKK":{n:"DNB Bank",c:"オスロ"},
// 中国（追加）
"CMBCCNBS":{n:"招商銀行（China Merchants Bank）",c:"深圳"},
// シンガポール（追加）
"SCBLSGSG":{n:"Standard Chartered Bank",c:"シンガポール"},
// 台湾
"BKTWTWTP":{n:"台湾銀行（Bank of Taiwan）",c:"台北"},
"ICBCTWTP":{n:"兆豐國際商業銀行（Mega Int'l Commercial Bank）",c:"台北"},
"CTCBTWTP":{n:"中國信託商業銀行（CTBC Bank）",c:"台北"},
// 韓国（追加）
"HVBKKRSE":{n:"Woori Bank（ウリ銀行）",c:"ソウル"},
"KOEXKRSE":{n:"Hana Bank（ハナ銀行）",c:"ソウル"},
"IBKOKRSE":{n:"Industrial Bank of Korea（IBK）",c:"ソウル"},
// マレーシア
"MBBEMYKL":{n:"Maybank",c:"クアラルンプール"},
"CIBBMYKL":{n:"CIMB Bank",c:"クアラルンプール"},
"PBBEMYKL":{n:"Public Bank",c:"クアラルンプール"},
// インド（追加）
"PUNBINBB":{n:"Punjab National Bank（PNB）",c:"ニューデリー"},
"BARBINBB":{n:"Bank of Baroda",c:"ムンバイ"},
"CNRBINBB":{n:"Canara Bank",c:"バンガロール"},
"KKBKINBB":{n:"Kotak Mahindra Bank",c:"ムンバイ"},
"UBININBB":{n:"Union Bank of India",c:"ムンバイ"},
// フィリピン（追加）
"RCBCPHMM":{n:"RCBC（Rizal Commercial Banking）",c:"マニラ"},
"UBPHPHMM":{n:"UnionBank of the Philippines",c:"マニラ"},
// ベトナム（追加）
"TCBKVNVX":{n:"Techcombank",c:"ハノイ"},
"VPBKVNVX":{n:"VPBank",c:"ハノイ"},
"ASCBVNVX":{n:"Asia Commercial Bank（ACB）",c:"ホーチミン"},
// インドネシア（追加）
"BDINIDJA":{n:"Bank Danamon",c:"ジャカルタ"},
// タイ（追加）
"TMBKTHBK":{n:"TMBThanachart Bank（ttb）",c:"バンコク"},
// カンボジア
"ABAAKHPP":{n:"ABA Bank",c:"プノンペン"},
"ACLBKHPP":{n:"ACLEDA Bank",c:"プノンペン"},
"CANDKHPP":{n:"Canadia Bank",c:"プノンペン"},
// ネパール（追加）
"SCBLNPKA":{n:"Standard Chartered Bank Nepal",c:"カトマンズ"},
// バングラデシュ
"SCBLBDDX":{n:"Standard Chartered Bank",c:"ダッカ"},
"IBBLBDDH":{n:"Islami Bank Bangladesh",c:"ダッカ"},
// パキスタン
"HABBPKKA":{n:"Habib Bank（HBL）",c:"カラチ"},
"UNILPKKA":{n:"United Bank（UBL）",c:"カラチ"},
"NBPAPKKA":{n:"National Bank of Pakistan",c:"カラチ"},
"SCBLPKKX":{n:"Standard Chartered Bank Pakistan",c:"カラチ"},
// スリランカ
"BCEYLKLX":{n:"Bank of Ceylon",c:"コロンボ"},
"CCEYLKLX":{n:"Commercial Bank of Ceylon",c:"コロンボ"},
// アラブ首長国連邦
"EBILAEAD":{n:"Emirates NBD",c:"ドバイ"},
"NBADAEAA":{n:"First Abu Dhabi Bank（FAB）",c:"アブダビ"},
// ブラジル
"BRASBRRJ":{n:"Banco do Brasil",c:"ブラジリア"},
"ITAUBRSP":{n:"Itaú Unibanco",c:"サンパウロ"},
"BRADBRSP":{n:"Banco Bradesco",c:"オザスコ"},
// メキシコ
"BNMXMXMM":{n:"Citibanamex（Banco Nacional de México）",c:"メキシコシティ"},
"BCMRMXMM":{n:"BBVA México",c:"メキシコシティ"},
// トルコ
"ISBKTRIS":{n:"Türkiye İş Bankası",c:"イスタンブール"},
"TCZBTR2A":{n:"Ziraat Bankası",c:"アンカラ"}
};
