module rex::rex {
    
    use sui::table::{Self, Table};
    use std::string::String;
    use sui::event;


    public struct Submissions has key {
        id: UID,
        submissions: Table<u64, Submission>,
        counter: u64,
    }

    public struct Submission has key, store {
        id: UID,
        caseId: u64,
        author: address,
        clarity: u8,
        plausibility: u8,
        consistency: u8,
        relevance: u8,
        is_safe: bool,
        flag: String,
        theory: String,
        summary: String,
        rank: String,
        timestamp: u64
    }

    public struct ValidSubmission has key, store {
        id: UID,
        caseId: u64,
        author: address,
        score: u8, // overall score based on clarity, plausibility, consistency, relevance and is_safe
        summary: String,
        rank: String, // rank based on score
        timestamp: u64,
    }

    public struct UserReputation has key {
        id: UID,
        wallet: address,
        reputation_points: u64,
        nft_count: u64,
        submissions_accepted: u64,
    }

    // Events
    public struct SubmissionSubmitted has copy, drop {
        id: u64,
        caseId: u64,
        author: address,
        summary: String,
        timestamp: u64
    }

    public struct NFTMinted has copy, drop {
        id: address,
        caseId: u64,
        author: address,
        score: u8,
        rank: String,
        summary: String,
        timestamp: u64
    }

    public struct ReputationUpdated has copy, drop {
        wallet: address,
        new_points: u64,
        nft_count: u64,
        submissions_accepted: u64
    }

    public struct UserStatsViewed has copy, drop {
        wallet: address,
        reputation_points: u64,
        nft_count: u64,
        submissions_accepted: u64
    }
    public struct SubmissionCounter has copy, drop {
        counter: u64
    }

    public struct ViewSubmission has copy, drop {
        caseId: u64,
        author: address,
        clarity: u8,
        plausibility: u8,
        consistency: u8,
        relevance: u8,
        is_safe: bool,
        flag: String,
        theory: String,
        summary: String,
        rank: String,
        timestamp: u64
    }
    
    fun init(ctx: &mut TxContext) {
        let sub_store = Submissions {
            id: object::new(ctx),
            submissions: table::new<u64, Submission>(ctx),
            counter: 0
        };
        transfer::share_object(sub_store);
    }
    
    public fun submit_submission(
        store: &mut Submissions,
        caseId: u64,
        author: address, 
        clarity: u8,
        plausibility: u8,
        consistency: u8,
        relevance: u8,
        is_safe: bool,
        flag: String,
        theory: String,
        summary: String,
        rank: String,
        timestamp: u64,
        ctx: &mut TxContext
    ) {
        let id = object::new(ctx);
        let current_count = store.counter;
        
        let submission = Submission {
            id,
            caseId,
            author,
            clarity,
            plausibility,
            consistency,
            relevance,
            is_safe,
            flag,
            theory,
            summary,
            rank,
            timestamp
        };

        table::add(&mut store.submissions, store.counter, submission);
        store.counter = store.counter + 1;
        
        // Emit event
        event::emit(SubmissionSubmitted {
            id: current_count,
            caseId,
            author,
            summary,
            timestamp,
        });
    }

    public fun mint_nft(
        caseId: u64,
        author: address,
        score: u8,
        summary: String,
        rank: String,
        timestamp: u64,
        ctx: &mut TxContext
    ) {
        let id = object::new(ctx);
        let nft_address = object::uid_to_address(&id);
        
        let nft = ValidSubmission {
            id,
            caseId,
            author,
            score,
            summary,
            rank,
            timestamp
        };
        
        // Emit event
        event::emit(NFTMinted {
            id: nft_address,
            caseId,
            author,
            score,
            rank,
            summary,
            timestamp
        });
        transfer::public_transfer(nft, author);
    }

    public fun create_user_reputation(
        user: address,
        ctx: &mut TxContext
    ) {
        let reputation = UserReputation {
            id: object::new(ctx),
            wallet: user,
            reputation_points: 0,
            nft_count: 0,
            submissions_accepted: 0,
        };
        transfer::transfer(reputation, user);
    }
    
    public fun update_reputation(
        user_rep: &mut UserReputation,
        points_to_add: u64,
        nft_minted: bool
    ) {
        user_rep.reputation_points = user_rep.reputation_points + points_to_add;
        user_rep.submissions_accepted = user_rep.submissions_accepted + 1;
        
        if (nft_minted) {
            user_rep.nft_count = user_rep.nft_count + 1;
        };
        
        // Emit event
        event::emit(ReputationUpdated {
            wallet: user_rep.wallet,
            new_points: user_rep.reputation_points,
            nft_count: user_rep.nft_count,
            submissions_accepted: user_rep.submissions_accepted
        });
    }
    
    // View function to get prediction by index
    public fun get_submission(store: &Submissions, index: u64): (u64, address, u8, u8, u8, u8, bool, String, String, String, String, u64) {
        let submission = table::borrow(&store.submissions, index);

        event::emit(ViewSubmission {
            caseId: submission.caseId,
            author: submission.author,
            clarity: submission.clarity,
            plausibility: submission.plausibility,
            consistency: submission.consistency,
            relevance: submission.relevance,
            is_safe: submission.is_safe,
            flag: submission.flag,
            theory: submission.theory,
            summary: submission.summary,
            rank: submission.rank,
            timestamp: submission.timestamp
        });
        (
            submission.caseId,
            submission.author,
            submission.clarity,
            submission.plausibility,
            submission.consistency,
            submission.relevance,
            submission.is_safe,
            submission.flag,
            submission.theory,
            submission.summary,
            submission.rank,
            submission.timestamp
        )
    }
    
    // Get total predictions count
    public fun get_submissions_count(store: &Submissions): u64 {
        event::emit(SubmissionCounter {
            counter: store.counter,
        });
        store.counter
    }
    
    // Get user reputation stats 
    public fun get_user_stats(user_rep: &UserReputation): (u64, u64, u64) {
        // Emit an event with the stats
        event::emit(UserStatsViewed {
            wallet: user_rep.wallet,
            reputation_points: user_rep.reputation_points,
            nft_count: user_rep.nft_count,
            submissions_accepted: user_rep.submissions_accepted
        });
        
        (
            user_rep.reputation_points,
            user_rep.nft_count,
            user_rep.submissions_accepted
        )
    }
}
